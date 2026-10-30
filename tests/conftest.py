"""Fixtures create a fresh, temporary database for each test."""

import pytest
from app import create_app
from app.extensions import db


@pytest.fixture
def app(tmp_path, monkeypatch):
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret-" * 4,
            "SQLALCHEMY_DATABASE_URI": f'sqlite:///{tmp_path / "test.db"}',
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,
            "PRODUCTION": False,
            "MAIL_MODE": "console",
            "SESSION_COOKIE_SECURE": False,
            "REMEMBER_COOKIE_SECURE": False,
        }
    )
    from datetime import date

    # Stable calendar date makes recurrence and dashboard tests reproducible.
    for module in ["app.services", "app.expenses.routes", "app.reports.routes"]:
        monkeypatch.setattr(module + ".today", lambda: date(2026, 10, 30))
    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, email="student@example.com", name="Student"):
    return client.post(
        "/auth/register",
        data={
            "name": name,
            "email": email,
            "password": "correct-horse-123",
            "confirm": "correct-horse-123",
        },
        follow_redirects=True,
    )


def login(client, email="student@example.com", password="correct-horse-123", remember=False):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password, "remember": "y" if remember else ""},
    )


@pytest.fixture
def signed_in(client, app):
    register(client)
    login(client)
    return client


def category_id(app, email="student@example.com", name="Food"):
    from app.models import Category, User

    with app.app_context():
        return db.session.scalar(
            db.select(Category.id)
            .join(User, Category.user_id == User.id)
            .where(User.email == email, Category.name == name)
        )


def transaction_data(cid, **overrides):
    data = {
        "kind": "expense",
        "amount": "120.50",
        "category_id": cid,
        "date": "2026-10-15",
        "payment_method": "UPI",
        "notes": "Lunch",
    }
    data.update(overrides)
    return data
