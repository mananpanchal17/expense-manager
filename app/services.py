"""Small reusable functions keep the route handlers easy to read."""

import calendar
import secrets
import smtplib
from datetime import date, datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage
from zoneinfo import ZoneInfo
from flask import current_app, abort, request
from flask_login import current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import func, or_
from .extensions import db
from .models import User, Category, Transaction, Budget, RecurringExpense, ActivityLog


def today():
    return datetime.now(ZoneInfo(current_app.config["APP_TIMEZONE"])).date()


def minor(value):
    return int(Decimal(value) * 100)


def log_event(user_id, event):
    db.session.add(ActivityLog(user_id=user_id, event=event))


def owned(model, record_id):
    """Never fetch a private record using its ID alone."""
    row = db.session.scalar(
        db.select(model).where(model.id == record_id, model.user_id == current_user.id)
    )
    if row is None:
        abort(404)
    return row


def category_choices(user_id):
    return [
        (c.id, c.name)
        for c in db.session.scalars(
            db.select(Category).where(Category.user_id == user_id).order_by(Category.name)
        )
    ]


def month_end(start):
    return date(start.year + (start.month == 12), start.month % 12 + 1, 1)


def budget_status(user_id, month):
    spent = dict(
        db.session.execute(
            db.select(Transaction.category_id, func.sum(Transaction.amount_minor))
            .where(
                Transaction.user_id == user_id,
                Transaction.kind == "expense",
                Transaction.date >= month,
                Transaction.date < month_end(month),
            )
            .group_by(Transaction.category_id)
        ).all()
    )
    result = []
    for budget in db.session.scalars(
        db.select(Budget).where(Budget.user_id == user_id, Budget.month == month)
    ):
        used = spent.get(budget.category_id, 0)
        percent = used * 100 / budget.amount_minor
        result.append(
            {
                "budget": budget,
                "spent": used,
                "percent": percent,
                "level": "danger" if percent >= 100 else "warning" if percent >= 80 else "success",
            }
        )
    return result


def warn_budgets(user_id, month):
    from flask import flash

    for item in budget_status(user_id, month.replace(day=1)):
        if item["percent"] >= 80:
            flash(
                f"{item['budget'].category.name}: {item['percent']:.0f}% of the monthly budget used.",
                item["level"],
            )


def advance_due(rule, due):
    if rule.frequency == "weekly":
        return due + timedelta(days=7)
    year = due.year + (rule.frequency == "yearly" or due.month == 12)
    month = due.month if rule.frequency == "yearly" else due.month % 12 + 1
    return date(year, month, min(rule.anchor_day, calendar.monthrange(year, month)[1]))


def process_recurring(user_id=None):
    """Claim each occurrence atomically, then insert it in the same transaction.

    The conditional UPDATE prevents two workers from claiming the same date.
    The unique occurrence constraint is a second guard against duplicates.
    """
    query = db.select(RecurringExpense).where(
        RecurringExpense.active.is_(True), RecurringExpense.next_due <= today()
    )
    if user_id is not None:
        query = query.where(RecurringExpense.user_id == user_id)
    rules = db.session.scalars(query).all()
    count = 0
    for rule in rules:
        due = rule.next_due
        while due <= today():
            following = advance_due(rule, due)
            claim = db.session.execute(
                db.update(RecurringExpense)
                .where(
                    RecurringExpense.id == rule.id,
                    RecurringExpense.next_due == due,
                    RecurringExpense.active.is_(True),
                )
                .values(next_due=following)
                .execution_options(synchronize_session=False)
            )
            if claim.rowcount != 1:
                break
            exists = db.session.scalar(
                db.select(Transaction.id).where(
                    Transaction.recurring_id == rule.id, Transaction.occurrence_date == due
                )
            )
            if not exists:
                db.session.add(
                    Transaction(
                        user_id=rule.user_id,
                        category_id=rule.category_id,
                        amount_minor=rule.amount_minor,
                        kind="expense",
                        date=due,
                        occurrence_date=due,
                        payment_method=rule.payment_method,
                        notes=rule.notes,
                        recurring_id=rule.id,
                    )
                )
                count += 1
            due = following
    if count:
        users = {r.user_id for r in rules}
        for uid in users:
            log_event(uid, "Processed due recurring expenses")
    db.session.commit()
    db.session.expire_all()
    return count


def reset_token(user):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"id": user.id, "version": user.session_token}, salt="password-reset")


def user_from_reset(token):
    try:
        data = URLSafeTimedSerializer(current_app.config["SECRET_KEY"]).loads(
            token, salt="password-reset", max_age=current_app.config["RESET_TOKEN_MAX_AGE"]
        )
        user = db.session.get(User, data["id"])
        if user and secrets.compare_digest(user.session_token, data["version"]):
            return user
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        pass
    return None


def send_reset_email(user):
    # Build from trusted config, never the client-supplied Host header.
    link = current_app.config["APP_BASE_URL"] + "/auth/reset/" + reset_token(user)
    if current_app.config["MAIL_MODE"] == "console":
        current_app.logger.warning("LOCAL DEVELOPMENT reset link for %s: %s", user.email, link)
        return
    message = EmailMessage()
    message["Subject"] = "Reset your Expense Manager password"
    message["From"] = current_app.config["MAIL_FROM"]
    message["To"] = user.email
    message.set_content(
        f"Reset your password using this link (expires in 30 minutes):\n{link}\n\nIf you did not request this, ignore this email."
    )
    import ssl

    with smtplib.SMTP(
        current_app.config["MAIL_SERVER"], current_app.config["MAIL_PORT"], timeout=10
    ) as smtp:
        if current_app.config["MAIL_USE_TLS"]:
            smtp.starttls(context=ssl.create_default_context())
        if current_app.config["MAIL_USERNAME"]:
            smtp.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
        smtp.send_message(message)


def filtered_transactions(user_id):
    """Use explicit whitelists for sort columns; input never becomes SQL text."""
    query = db.select(Transaction).join(Category).where(Transaction.user_id == user_id)
    args = request.args
    if args.get("q"):
        text = args["q"][:100]
        query = query.where(
            or_(
                Transaction.notes.contains(text, autoescape=True),
                Category.name.contains(text, autoescape=True),
            )
        )
    try:
        start = date.fromisoformat(args["start"]) if args.get("start") else None
        end = date.fromisoformat(args["end"]) if args.get("end") else None
        if start and end and start > end:
            raise ValueError()
        if start:
            query = query.where(Transaction.date >= start)
        if end:
            query = query.where(Transaction.date <= end)
        if args.get("category"):
            category_id = int(args["category"])
            owned(Category, category_id)
            query = query.where(Transaction.category_id == category_id)
        if args.get("kind"):
            if args["kind"] not in ("income", "expense"):
                raise ValueError()
            query = query.where(Transaction.kind == args["kind"])
        amounts = {}
        for key in ["min_amount", "max_amount"]:
            if args.get(key):
                amount = Decimal(args[key])
                if (
                    not amount.is_finite()
                    or amount < 0
                    or amount > Decimal("999999999.99")
                    or amount != amount.quantize(Decimal(".01"))
                ):
                    raise ValueError()
                amounts[key] = minor(amount)
        if amounts.get("min_amount", 0) > amounts.get("max_amount", 99999999999):
            raise ValueError()
        if "min_amount" in amounts:
            query = query.where(Transaction.amount_minor >= amounts["min_amount"])
        if "max_amount" in amounts:
            query = query.where(Transaction.amount_minor <= amounts["max_amount"])
    except (ValueError, ArithmeticError):
        abort(400)
    sorting = {
        "date_desc": Transaction.date.desc(),
        "date_asc": Transaction.date.asc(),
        "amount_desc": Transaction.amount_minor.desc(),
        "amount_asc": Transaction.amount_minor.asc(),
        "category": Category.name.asc(),
    }
    if args.get("sort", "date_desc") not in sorting:
        abort(400)
    return query.order_by(sorting[args.get("sort", "date_desc")], Transaction.id.desc())
