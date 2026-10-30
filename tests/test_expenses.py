import io
from datetime import date
from app.extensions import db
from app.models import Transaction, Budget, RecurringExpense, Category
from app.services import budget_status, process_recurring, advance_due
from conftest import category_id, transaction_data, register, login


def test_expense_crud_and_exact_money(signed_in, app):
    cid = category_id(app)
    assert signed_in.post("/expenses/add", data=transaction_data(cid)).status_code == 302
    with app.app_context():
        row = db.session.scalar(db.select(Transaction))
        assert row.amount_minor == 12050
        record_id = row.id
    assert b"120.50" in signed_in.get("/expenses/").data
    assert (
        signed_in.post(
            f"/expenses/{record_id}/edit", data=transaction_data(cid, amount="99.99", kind="income")
        ).status_code
        == 302
    )
    with app.app_context():
        row = db.session.get(Transaction, record_id)
        assert (row.amount_minor, row.kind) == (9999, "income")
    assert signed_in.post(f"/expenses/{record_id}/delete").status_code == 302
    with app.app_context():
        assert db.session.get(Transaction, record_id) is None


def test_invalid_amounts_rejected(signed_in, app):
    cid = category_id(app)
    for amount in ["0", "-10", "1.999", "NaN", "Infinity", "9999999999999", "abc"]:
        response = signed_in.post("/expenses/add", data=transaction_data(cid, amount=amount))
        assert response.status_code == 200
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Transaction.id))) == 0


def test_isolation_for_records_and_category_form(signed_in, app):
    cid = category_id(app)
    signed_in.post("/expenses/add", data=transaction_data(cid))
    signed_in.post(
        "/expenses/budgets", data={"category_id": cid, "amount": "500", "month": "2026-10"}
    )
    signed_in.post(
        "/expenses/recurring",
        data={
            "category_id": cid,
            "amount": "100",
            "next_due": "2026-10-01",
            "frequency": "monthly",
            "payment_method": "UPI",
            "active": "y",
        },
    )
    with app.app_context():
        tid = db.session.scalar(db.select(Transaction.id))
        bid = db.session.scalar(db.select(Budget.id))
        rid = db.session.scalar(db.select(RecurringExpense.id))
    attacker = app.test_client()
    register(attacker, "other@example.com")
    login(attacker, "other@example.com")
    for path in [
        f"/expenses/{tid}/edit",
        f"/expenses/categories/{cid}/edit",
        f"/expenses/recurring/{rid}/edit",
    ]:
        assert attacker.get(path).status_code == 404
        assert attacker.post(path, data=transaction_data(cid)).status_code == 404
    for path in [
        f"/expenses/{tid}/delete",
        f"/expenses/categories/{cid}/delete",
        f"/expenses/budgets/{bid}/delete",
        f"/expenses/recurring/{rid}/delete",
    ]:
        assert attacker.post(path).status_code == 404
    assert attacker.post("/expenses/add", data=transaction_data(cid)).status_code == 200
    assert b"120.50" not in attacker.get("/expenses/").data
    assert b"Lunch" not in attacker.get("/export/csv").data
    assert attacker.get(f"/expenses/?category={cid}").status_code == 404


def test_search_filter_sort_and_invalid_ranges(signed_in, app):
    cid = category_id(app)
    signed_in.post("/expenses/add", data=transaction_data(cid, notes="Coffee", amount="50"))
    signed_in.post("/expenses/add", data=transaction_data(cid, notes="Dinner", amount="200"))
    page = signed_in.get(
        "/expenses/?q=Coffee&start=2026-10-01&end=2026-10-31&min_amount=10&max_amount=100"
    ).data
    assert b"Coffee" in page and b"Dinner" not in page
    page = signed_in.get("/expenses/?sort=amount_desc").data.split(b"<tbody>")[1]
    assert page.index(b"Dinner") < page.index(b"Coffee")
    for query in [
        "start=oops",
        "min_amount=NaN",
        "min_amount=20&max_amount=10",
        "start=2026-10-31&end=2026-10-01",
        "sort=DROP",
        "kind=anything",
    ]:
        assert signed_in.get("/expenses/?" + query).status_code == 400


def test_categories_duplicate_edit_and_in_use_delete(signed_in, app):
    assert signed_in.post("/expenses/categories", data={"name": "Books"}).status_code == 302
    assert b"already have" in signed_in.post("/expenses/categories", data={"name": "books"}).data
    bid = category_id(app, name="Books")
    assert (
        signed_in.post(f"/expenses/categories/{bid}/edit", data={"name": "Study"}).status_code
        == 302
    )
    signed_in.post("/expenses/add", data=transaction_data(bid))
    assert (
        b"in use"
        in signed_in.post(f"/expenses/categories/{bid}/delete", follow_redirects=True).data
    )
    unused = category_id(app, name="Shopping")
    assert signed_in.post(f"/expenses/categories/{unused}/delete").status_code == 302
    with app.app_context():
        assert db.session.get(Category, unused) is None


def test_budget_thresholds_and_upsert(signed_in, app):
    cid = category_id(app)
    signed_in.post(
        "/expenses/budgets", data={"category_id": cid, "amount": "100", "month": "2026-10"}
    )
    response = signed_in.post(
        "/expenses/add", data=transaction_data(cid, amount="80"), follow_redirects=True
    )
    assert b"80% of the monthly budget" in response.data
    with app.app_context():
        budget = db.session.scalar(db.select(Budget))
        assert budget_status(budget.user_id, date(2026, 10, 1))[0]["level"] == "warning"
    signed_in.post("/expenses/add", data=transaction_data(cid, amount="20"))
    with app.app_context():
        budget = db.session.scalar(db.select(Budget))
        assert budget_status(budget.user_id, date(2026, 10, 1))[0]["level"] == "danger"
    signed_in.post(
        "/expenses/budgets", data={"category_id": cid, "amount": "500", "month": "2026-10"}
    )
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Budget.id))) == 1
        assert db.session.scalar(db.select(Budget.amount_minor)) == 50000


def test_recurring_catchup_is_idempotent(signed_in, app, monkeypatch):
    monkeypatch.setattr("app.services.today", lambda: date(2026, 3, 31))
    cid = category_id(app)
    response = signed_in.post(
        "/expenses/recurring",
        data={
            "category_id": cid,
            "amount": "2000",
            "next_due": "2026-01-31",
            "frequency": "monthly",
            "payment_method": "Bank transfer",
            "active": "y",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        assert process_recurring() == 3
        assert process_recurring() == 0
        rows = db.session.scalars(db.select(Transaction).order_by(Transaction.date)).all()
        assert [r.date for r in rows] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
        rule = db.session.scalar(db.select(RecurringExpense))
        assert rule.next_due == date(2026, 4, 30)
        rid = rule.id
    assert signed_in.post(f"/expenses/recurring/{rid}/delete").status_code == 302
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Transaction.id))) == 3
        assert db.session.scalar(db.select(Transaction.recurring_id)) is None


def test_recurring_leap_year_and_paused(app):
    rule = RecurringExpense(frequency="yearly", anchor_day=29)
    assert advance_due(rule, date(2024, 2, 29)) == date(2025, 2, 28)
    assert advance_due(rule, date(2027, 2, 28)) == date(2028, 2, 29)
    rule.frequency = "weekly"
    assert advance_due(rule, date(2026, 12, 29)) == date(2027, 1, 5)


def upload(client, body):
    return client.post(
        "/expenses/import",
        data={"file": (io.BytesIO(body.encode()), "expenses.csv")},
        content_type="multipart/form-data",
    )


def test_csv_import_atomic_and_valid(signed_in, app):
    header = "kind,amount,category,date,payment_method,notes\n"
    good = "expense,25.50,Food,2026-10-15,UPI,Imported lunch\n"
    bad = "expense,-5,Food,2026-10-15,UPI,Invalid\n"
    response = upload(signed_in, header + good + bad)
    assert b"Row 3" in response.data
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Transaction.id))) == 0
    assert upload(signed_in, header + good).status_code == 302
    with app.app_context():
        assert db.session.scalar(db.select(Transaction.amount_minor)) == 2550


def test_export_formats_filters_and_formula_escape(signed_in, app):
    cid = category_id(app)
    signed_in.post("/expenses/add", data=transaction_data(cid, notes='=HYPERLINK("bad")'))
    csv_response = signed_in.get("/export/csv")
    assert csv_response.status_code == 200 and b"'=HYPERLINK" in csv_response.data
    assert b"120.50" not in signed_in.get("/export/csv?start=2027-01-01").data
    pdf_response = signed_in.get("/export/pdf")
    assert pdf_response.status_code == 200 and pdf_response.data.startswith(b"%PDF")


def test_dashboard_reports_and_charts(signed_in, app, monkeypatch):
    monkeypatch.setattr("app.reports.routes.today", lambda: date(2026, 10, 30))
    cid = category_id(app)
    signed_in.post("/expenses/add", data=transaction_data(cid, amount="10"))
    signed_in.post("/expenses/add", data=transaction_data(cid, amount="100", kind="income"))
    for path in [
        "/",
        "/expenses/",
        "/expenses/add",
        "/expenses/categories",
        "/expenses/budgets",
        "/expenses/recurring",
        "/expenses/import",
        "/auth/profile",
        "/reports/monthly",
        "/reports/yearly",
    ]:
        assert signed_in.get(path).status_code == 200, path
    data = signed_in.get("/reports/chart-data").json
    assert len(data["labels"]) == 12
    assert data["income"][-1] == 100 and data["expense"][-1] == 10
    assert data["category_values"] == [10]
    assert b"INR 90.00" in signed_in.get("/reports/monthly?year=2026&month=10").data


def test_recurring_concurrent_runs_and_paused_rule(signed_in, app):
    from concurrent.futures import ThreadPoolExecutor

    cid = category_id(app)
    signed_in.post(
        "/expenses/recurring",
        data={
            "category_id": cid,
            "amount": "100",
            "next_due": "2026-10-01",
            "frequency": "weekly",
            "payment_method": "UPI",
            "active": "y",
        },
    )

    def run_job():
        with app.app_context():
            return process_recurring()

    with ThreadPoolExecutor(max_workers=2) as pool:
        counts = list(pool.map(lambda _: run_job(), range(2)))
    assert sum(counts) == 5
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Transaction.id))) == 5
        rule = db.session.scalar(db.select(RecurringExpense))
        rule.next_due = date(2026, 10, 30)
        rule.active = False
        db.session.commit()
        assert process_recurring() == 0


def test_pdf_long_notes_multiple_pages_and_no_markup_execution(signed_in, app):
    cid = category_id(app)
    with app.app_context():
        uid = db.session.get(Category, cid).user_id
        for _ in range(35):
            db.session.add(
                Transaction(
                    user_id=uid,
                    category_id=cid,
                    kind="expense",
                    amount_minor=100,
                    date=date(2026, 10, 15),
                    payment_method="Cash",
                    notes=("<b>Plain text</b> & " + "long note " * 40)[:500],
                )
            )
        db.session.commit()
    response = signed_in.get("/export/pdf")
    assert response.status_code == 200
    assert response.data.startswith(b"%PDF")
    assert len(response.data) > 10000
