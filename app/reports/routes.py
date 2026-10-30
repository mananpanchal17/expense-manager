"""Dashboard charts, monthly/yearly summaries, and filtered CSV/PDF exports."""

import csv
import io
from collections import defaultdict
from datetime import date
from decimal import Decimal
from xml.sax.saxutils import escape
from flask import Blueprint, render_template, request, abort, Response, send_file, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from ..extensions import db
from ..models import Transaction, Category
from ..services import today, month_end, budget_status, filtered_transactions, log_event

bp = Blueprint("reports", __name__)


def totals(start=None, end=None):
    query = db.select(Transaction.kind, func.sum(Transaction.amount_minor)).where(
        Transaction.user_id == current_user.id
    )
    if start:
        query = query.where(Transaction.date >= start)
    if end:
        query = query.where(Transaction.date < end)
    values = dict(db.session.execute(query.group_by(Transaction.kind)).all())
    income, expense = values.get("income", 0), values.get("expense", 0)
    return {"income": income, "expense": expense, "balance": income - expense}


@bp.get("/")
@login_required
def dashboard():
    start = today().replace(day=1)
    recent = db.session.scalars(
        db.select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(6)
    ).all()
    return render_template(
        "reports/dashboard.html",
        title="Overview",
        summary=totals(),
        month_spend=totals(start, month_end(start))["expense"],
        budgets=budget_status(current_user.id, start),
        recent=recent,
    )


@bp.get("/reports/chart-data")
@login_required
def chart_data():
    month = today().replace(day=1)
    first = date(month.year - 1, month.month + 1, 1) if month.month < 12 else date(month.year, 1, 1)
    rows = db.session.scalars(
        db.select(Transaction).where(
            Transaction.user_id == current_user.id,
            Transaction.date >= first,
            Transaction.date < month_end(month),
        )
    ).all()
    monthly = defaultdict(lambda: {"income": 0, "expense": 0})
    for row in rows:
        monthly[row.date.strftime("%Y-%m")][row.kind] += row.amount_minor
    labels = []
    cursor = first
    while cursor <= month:
        labels.append(cursor.strftime("%Y-%m"))
        cursor = month_end(cursor)
    categories = db.session.execute(
        db.select(Category.name, func.sum(Transaction.amount_minor))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == current_user.id,
            Transaction.kind == "expense",
            Transaction.date >= month,
            Transaction.date < month_end(month),
        )
        .group_by(Category.id, Category.name)
        .order_by(Category.name)
    ).all()
    return jsonify(
        {
            "labels": labels,
            "income": [monthly[x]["income"] / 100 for x in labels],
            "expense": [monthly[x]["expense"] / 100 for x in labels],
            "category_labels": [r[0] for r in categories],
            "category_values": [r[1] / 100 for r in categories],
            "currency": current_user.currency,
        }
    )


@bp.get("/reports/<period>")
@login_required
def report(period):
    if period not in ["monthly", "yearly"]:
        abort(404)
    try:
        year = int(request.args.get("year", today().year))
        month = int(request.args.get("month", today().month))
        if not 1900 <= year <= 9998 or not 1 <= month <= 12:
            raise ValueError()
    except ValueError:
        abort(400)
    start = date(year, month if period == "monthly" else 1, 1)
    end = month_end(start) if period == "monthly" else date(year + 1, 1, 1)
    rows = db.session.execute(
        db.select(Category.name, Transaction.kind, func.sum(Transaction.amount_minor))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == current_user.id,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Category.id, Category.name, Transaction.kind)
        .order_by(Category.name)
    ).all()
    month_rows = []
    if period == "yearly":
        cursor = start
        while cursor < end:
            month_rows.append((cursor.strftime("%B"), totals(cursor, month_end(cursor))))
            cursor = month_end(cursor)
    from datetime import timedelta

    return render_template(
        "reports/report.html",
        title=period.title() + " report",
        period=period,
        year=year,
        month=month,
        summary=totals(start, end),
        rows=rows,
        month_rows=month_rows,
        start=start,
        end=end - timedelta(days=1),
    )


def csv_safe(value):
    # Spreadsheet apps interpret leading =,+,-,@ as formulas, even in quoted cells.
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


@bp.get("/export/csv")
@login_required
def export_csv():
    rows = db.session.scalars(filtered_transactions(current_user.id)).all()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["kind", "amount", "category", "date", "payment_method", "notes"])
    for row in rows:
        writer.writerow(
            [
                row.kind,
                f"{Decimal(row.amount_minor) / 100:.2f}",
                csv_safe(row.category.name),
                row.date.isoformat(),
                row.payment_method,
                csv_safe(row.notes),
            ]
        )
    log_event(current_user.id, "Exported CSV")
    db.session.commit()
    return Response(
        "\ufeff" + buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@bp.get("/export/pdf")
@login_required
def export_pdf():
    rows = db.session.scalars(filtered_transactions(current_user.id).limit(2001)).all()
    if len(rows) > 2000:
        from flask import flash, redirect, url_for

        flash("PDF export is limited to 2,000 rows. Narrow the date range or use CSV.", "warning")
        return redirect(url_for("expenses.index", **request.args))
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    # DejaVu is used when available; bundling a Unicode font is described in README.
    import os
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_file = os.path.join(os.path.dirname(__file__), "..", "static", "fonts", "DejaVuSans.ttf")
    font = "Helvetica"
    if os.path.exists(font_file):
        if "DejaVuSans" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_file))
        font = "DejaVuSans"
    styles["BodyText"].fontName = font
    styles["BodyText"].fontSize = 8
    styles["BodyText"].leading = 11

    def paragraph(value):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["BodyText"])

    income = sum(r.amount_minor for r in rows if r.kind == "income")
    expense = sum(r.amount_minor for r in rows if r.kind == "expense")
    story = [
        Paragraph("Expense Manager | Transaction report", styles["Title"]),
        paragraph(
            f"Currency: {current_user.currency} | Generated: {today()} | {len(rows)} records"
        ),
        paragraph(
            f"Income: {Decimal(income)/100:,.2f} | Expenses: {Decimal(expense)/100:,.2f} | Balance: {Decimal(income-expense)/100:,.2f}"
        ),
        Spacer(1, 15),
    ]
    data = [[paragraph(x) for x in ["Date", "Type", "Category", "Amount", "Payment", "Notes"]]]
    for row in rows:
        data.append(
            [
                paragraph(x)
                for x in [
                    row.date,
                    row.kind.title(),
                    row.category.name,
                    f"{Decimal(row.amount_minor)/100:,.2f}",
                    row.payment_method,
                    row.notes,
                ]
            ]
        )
    table = Table(data, colWidths=[65, 55, 100, 90, 90, 375], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dceee9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    story.append(table)

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(810, 16, f"Page {document.page}")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    log_event(current_user.id, "Exported PDF")
    db.session.commit()
    return send_file(
        output, mimetype="application/pdf", as_attachment=True, download_name="expense-report.pdf"
    )
