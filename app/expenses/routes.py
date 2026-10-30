"""Transaction CRUD, categories, budgets, recurring rules, and CSV import."""

import csv
import io
from datetime import date
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import MultiDict
from ..extensions import db
from ..models import Transaction, Category, Budget, RecurringExpense
from ..forms import TransactionForm, CategoryForm, BudgetForm, RecurringForm, ImportForm, BaseForm
from ..services import (
    owned,
    minor,
    category_choices,
    today,
    log_event,
    filtered_transactions,
    budget_status,
    warn_budgets,
    process_recurring,
)

bp = Blueprint("expenses", __name__, url_prefix="/expenses")


def form_categories(form):
    # WTForms rejects IDs absent from these user-specific choices.
    form.category_id.choices = category_choices(current_user.id)


def save_transaction(row, form):
    row.kind = form.kind.data
    row.amount_minor = minor(form.amount.data)
    row.category_id = form.category_id.data
    row.date = form.date.data
    row.payment_method = form.payment_method.data
    row.notes = form.notes.data or ""


@bp.get("/")
@login_required
def index():
    page = db.paginate(filtered_transactions(current_user.id), per_page=20, max_per_page=20)
    return render_template(
        "expenses/index.html",
        title="Transactions",
        page=page,
        categories=category_choices(current_user.id),
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add():
    form = TransactionForm()
    form_categories(form)
    if request.method == "GET":
        form.date.data = today()
    if form.validate_on_submit():
        row = Transaction(user_id=current_user.id)
        save_transaction(row, form)
        db.session.add(row)
        log_event(current_user.id, "Transaction added")
        db.session.commit()
        flash("Transaction added.", "success")
        warn_budgets(current_user.id, row.date)
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html", form=form, title="Add transaction")


@bp.route("/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit(record_id):
    row = owned(Transaction, record_id)
    form = TransactionForm(obj=row)
    form_categories(form)
    if request.method == "GET":
        form.amount.data = Decimal(row.amount_minor) / 100
    if form.validate_on_submit():
        save_transaction(row, form)
        log_event(current_user.id, "Transaction edited")
        db.session.commit()
        flash("Transaction updated.", "success")
        warn_budgets(current_user.id, row.date)
        return redirect(url_for("expenses.index"))
    return render_template("expenses/form.html", form=form, title="Edit transaction")


@bp.post("/<int:record_id>/delete")
@login_required
def delete(record_id):
    row = owned(Transaction, record_id)
    if BaseForm().validate_on_submit():
        db.session.delete(row)
        log_event(current_user.id, "Transaction deleted")
        db.session.commit()
        flash("Transaction deleted.", "success")
    return redirect(url_for("expenses.index"))


@bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        db.session.add(Category(user_id=current_user.id, name=form.name.data))
        log_event(current_user.id, "Category added")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("You already have a category with that name.")
        else:
            flash("Category added.", "success")
            return redirect(url_for("expenses.categories"))
    return render_template(
        "expenses/categories.html",
        title="Categories",
        form=form,
        categories=category_choices(current_user.id),
    )


@bp.route("/categories/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(record_id):
    row = owned(Category, record_id)
    form = CategoryForm(obj=row)
    if form.validate_on_submit():
        row.name = form.name.data
        log_event(current_user.id, "Category renamed")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.name.errors.append("You already have a category with that name.")
        else:
            flash("Category updated.", "success")
            return redirect(url_for("expenses.categories"))
    return render_template("expenses/form.html", form=form, title="Edit category")


@bp.post("/categories/<int:record_id>/delete")
@login_required
def delete_category(record_id):
    row = owned(Category, record_id)
    if BaseForm().validate_on_submit():
        in_use = any(
            db.session.scalar(db.select(model.id).where(model.category_id == row.id).limit(1))
            for model in [Transaction, Budget, RecurringExpense]
        )
        if in_use:
            flash(
                "Category is in use. Reassign or delete its transactions, budgets and recurring rules first.",
                "warning",
            )
        else:
            db.session.delete(row)
            log_event(current_user.id, "Category deleted")
            db.session.commit()
            flash("Category deleted.", "success")
    return redirect(url_for("expenses.categories"))


@bp.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    form = BudgetForm()
    form_categories(form)
    try:
        selected_month = date.fromisoformat(
            request.args.get("month", today().strftime("%Y-%m")) + "-01"
        )
        if not 1900 <= selected_month.year <= 9998:
            raise ValueError()
    except ValueError:
        abort(400)
    if request.method == "GET":
        form.month.data = selected_month.strftime("%Y-%m")
    if form.validate_on_submit():
        month = date.fromisoformat(form.month.data + "-01")
        row = db.session.scalar(
            db.select(Budget).where(
                Budget.user_id == current_user.id,
                Budget.category_id == form.category_id.data,
                Budget.month == month,
            )
        )
        if not row:
            row = Budget(user_id=current_user.id, category_id=form.category_id.data, month=month)
            db.session.add(row)
        row.amount_minor = minor(form.amount.data)
        log_event(current_user.id, "Monthly budget saved")
        db.session.commit()
        flash("Budget saved. Saving the same category and month updates its limit.", "success")
        return redirect(url_for("expenses.budgets", month=form.month.data))
    return render_template(
        "expenses/budgets.html",
        title="Monthly budgets",
        form=form,
        items=budget_status(current_user.id, selected_month),
        month=selected_month,
    )


@bp.post("/budgets/<int:record_id>/delete")
@login_required
def delete_budget(record_id):
    row = owned(Budget, record_id)
    if BaseForm().validate_on_submit():
        db.session.delete(row)
        log_event(current_user.id, "Budget deleted")
        db.session.commit()
        flash("Budget deleted.", "success")
    return redirect(url_for("expenses.budgets"))


@bp.route("/recurring", methods=["GET", "POST"])
@login_required
def recurring():
    form = RecurringForm()
    form_categories(form)
    if request.method == "GET":
        form.next_due.data = today()
    if form.validate_on_submit():
        row = RecurringExpense(user_id=current_user.id)
        save_rule(row, form)
        db.session.add(row)
        log_event(current_user.id, "Recurring expense added")
        db.session.commit()
        flash(
            "Recurring rule saved. Use Generate due expenses, or schedule the CLI command.",
            "success",
        )
        return redirect(url_for("expenses.recurring"))
    rules = db.session.scalars(
        db.select(RecurringExpense)
        .where(RecurringExpense.user_id == current_user.id)
        .order_by(RecurringExpense.next_due)
    ).all()
    return render_template(
        "expenses/recurring.html", title="Recurring expenses", form=form, rules=rules
    )


def save_rule(row, form):
    row.category_id = form.category_id.data
    row.amount_minor = minor(form.amount.data)
    if row.next_due != form.next_due.data:
        row.anchor_day = form.next_due.data.day
    row.next_due = form.next_due.data
    row.frequency = form.frequency.data
    row.payment_method = form.payment_method.data
    row.notes = form.notes.data or ""
    row.active = form.active.data


@bp.route("/recurring/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_recurring(record_id):
    row = owned(RecurringExpense, record_id)
    form = RecurringForm(obj=row)
    form_categories(form)
    if request.method == "GET":
        form.amount.data = Decimal(row.amount_minor) / 100
    if form.validate_on_submit():
        # Rewinding a rule can regenerate deleted history, so require a new rule instead.
        if form.next_due.data < row.next_due:
            form.next_due.errors.append(
                "The next date cannot move backwards. Create a new rule for historical entries."
            )
        else:
            save_rule(row, form)
            log_event(current_user.id, "Recurring expense updated")
            db.session.commit()
            flash("Recurring rule updated. Existing transactions are unchanged.", "success")
            return redirect(url_for("expenses.recurring"))
    return render_template("expenses/form.html", form=form, title="Edit recurring expense")


@bp.post("/recurring/<int:record_id>/delete")
@login_required
def delete_recurring(record_id):
    row = owned(RecurringExpense, record_id)
    if BaseForm().validate_on_submit():
        db.session.execute(
            db.update(Transaction)
            .where(Transaction.user_id == current_user.id, Transaction.recurring_id == row.id)
            .values(recurring_id=None)
        )
        db.session.delete(row)
        log_event(current_user.id, "Recurring rule deleted (transactions retained)")
        db.session.commit()
        flash("Rule deleted. Previously generated transactions were kept.", "success")
    return redirect(url_for("expenses.recurring"))


@bp.post("/recurring/generate")
@login_required
def generate_recurring():
    if BaseForm().validate_on_submit():
        count = process_recurring(current_user.id)
        flash(f"Generated {count} due transaction(s).", "success")
        warn_budgets(current_user.id, today())
    return redirect(url_for("expenses.recurring"))


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_csv():
    form = ImportForm()
    if form.validate_on_submit():
        try:
            text = form.file.data.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            required = {"kind", "amount", "category", "date", "payment_method", "notes"}
            if (
                not reader.fieldnames
                or set(reader.fieldnames) != required
                or len(reader.fieldnames) != len(required)
            ):
                raise ValueError(
                    "Use exactly these CSV headers: kind,amount,category,date,payment_method,notes."
                )
            choices = category_choices(current_user.id)
            by_name = {name.casefold(): cid for cid, name in choices}
            pending = []
            for line, data in enumerate(reader, 2):
                if line > 2001:
                    raise ValueError("Import at most 2,000 rows at a time.")
                if None in data or any(value is None for value in data.values()):
                    raise ValueError(f"Row {line}: wrong number of columns.")
                cid = by_name.get(data["category"].strip().casefold())
                if cid is None:
                    raise ValueError(
                        f"Row {line}: unknown category. Create that category before importing."
                    )
                data["category_id"] = str(cid)
                row_form = TransactionForm(MultiDict(data), meta={"csrf": False})
                row_form.category_id.choices = choices
                if not row_form.validate():
                    errors = "; ".join(
                        f'{key}: {", ".join(values)}' for key, values in row_form.errors.items()
                    )
                    raise ValueError(f"Row {line}: {errors}")
                row = Transaction(user_id=current_user.id)
                save_transaction(row, row_form)
                pending.append(row)
            if not pending:
                raise ValueError("The CSV has no transaction rows.")
            # Only write after EVERY row validates: all-or-nothing import.
            db.session.add_all(pending)
            log_event(current_user.id, f"Imported {len(pending)} transactions from CSV")
            db.session.commit()
            flash(f"Imported {len(pending)} transactions.", "success")
            warn_budgets(current_user.id, today())
            return redirect(url_for("expenses.index"))
        except (UnicodeDecodeError, csv.Error, ValueError) as error:
            db.session.rollback()
            form.file.errors.append(
                str(error)
                if not isinstance(error, UnicodeDecodeError)
                else "Save the CSV as UTF-8."
            )
    return render_template("expenses/import.html", form=form, title="Import CSV")
