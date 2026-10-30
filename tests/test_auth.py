from datetime import timedelta
from app.extensions import db
from app.models import User, ActivityLog, utcnow, Category, Transaction, Budget, RecurringExpense
from app.services import reset_token
from conftest import register, login, category_id, transaction_data


def test_registration_hash_login_logout(client, app):
    response = register(client)
    assert b"Account created" in response.data
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert user.password_hash != "correct-horse-123"
        assert user.check_password("correct-horse-123")
        assert len(user.categories) == 7
    assert login(client, remember=True).status_code == 302
    assert client.get("/").status_code == 200
    assert client.get_cookie("remember_token") is not None
    assert client.post("/auth/logout").status_code == 302
    assert client.get("/").status_code == 302


def test_duplicate_email_and_weak_password(client, app):
    register(client)
    assert b"cannot be registered" in register(client, email="STUDENT@example.com").data
    response = client.post(
        "/auth/register",
        data={"name": "X", "email": "new@example.com", "password": "short", "confirm": "short"},
    )
    assert b"10" in response.data
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(User.id))) == 1


def test_lockout_after_five_failures_and_expiry(client, app):
    register(client)
    for _ in range(5):
        login(client, password="wrong")
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert user.failed_attempts == 5
        assert user.locked_until > utcnow()
    assert login(client).status_code == 200  # Correct password still locked out.
    with app.app_context():
        user = db.session.scalar(db.select(User))
        user.locked_until = utcnow() - timedelta(seconds=1)
        db.session.commit()
    assert login(client).status_code == 302


def test_reset_single_use_invalidates_sessions(signed_in, app):
    with app.app_context():
        user = db.session.scalar(db.select(User))
        token = reset_token(user)
        old_session_token = user.session_token
    other = app.test_client()
    response = other.post(
        "/auth/reset/" + token, data={"password": "new-password-123", "confirm": "new-password-123"}
    )
    assert response.status_code == 302
    assert signed_in.get("/").status_code == 302
    assert other.get("/auth/reset/" + token).status_code == 302
    assert other.get("/auth/reset/tampered").status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert user.session_token != old_session_token
        assert user.check_password("new-password-123")


def test_expired_reset_token(client, app):
    register(client)
    with app.app_context():
        token = reset_token(db.session.scalar(db.select(User)))
    app.config["RESET_TOKEN_MAX_AGE"] = -1
    assert client.get("/auth/reset/" + token).status_code == 302


def test_forgot_password_generic_response(client, monkeypatch):
    register(client)
    sent = []
    monkeypatch.setattr("app.auth.routes.send_reset_email", lambda user: sent.append(user.email))
    first = client.post(
        "/auth/forgot-password", data={"email": "student@example.com"}, follow_redirects=True
    )
    second = client.post(
        "/auth/forgot-password", data={"email": "missing@example.com"}, follow_redirects=True
    )
    assert b"If this account exists" in first.data and b"If this account exists" in second.data
    assert sent == ["student@example.com"]


def test_profile_requires_current_password(signed_in, app):
    response = signed_in.post(
        "/auth/profile",
        data={
            "name": "New Name",
            "email": "student@example.com",
            "currency": "USD",
            "current_password": "wrong",
        },
    )
    assert b"Current password is incorrect" in response.data
    response = signed_in.post(
        "/auth/profile",
        data={
            "name": "New Name",
            "email": "student@example.com",
            "currency": "USD",
            "current_password": "correct-horse-123",
        },
    )
    assert response.status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(User))
        assert (user.name, user.currency) == ("New Name", "USD")


def test_delete_account_removes_all_owned_rows(signed_in, app):
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
    signed_in.post("/expenses/recurring/generate")
    response = signed_in.post(
        "/auth/delete-account", data={"password": "correct-horse-123", "confirmation": "DELETE"}
    )
    assert response.status_code == 302
    with app.app_context():
        for model in [User, Category, Transaction, Budget, RecurringExpense, ActivityLog]:
            assert db.session.scalar(db.select(db.func.count(model.id))) == 0
