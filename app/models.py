"""Database tables. All money values are integer minor units (paise/cents)."""

import secrets
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db


def utcnow():
    # Store naive UTC consistently in SQLite; dates use the configured local zone.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="INR")
    session_token = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: secrets.token_hex(32)
    )
    failed_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    categories = db.relationship("Category", backref="user", cascade="all, delete-orphan")
    transactions = db.relationship("Transaction", backref="user", cascade="all, delete-orphan")
    budgets = db.relationship("Budget", backref="user", cascade="all, delete-orphan")
    recurring_rules = db.relationship(
        "RecurringExpense", backref="user", cascade="all, delete-orphan"
    )
    logs = db.relationship("ActivityLog", backref="user", cascade="all, delete-orphan")

    def get_id(self):
        # Rotating this invalidates every existing session and remember-me cookie.
        return self.session_token

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        self.session_token = secrets.token_hex(32)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "name"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    name = db.Column(db.String(60, collation="NOCASE"), nullable=False)


class Transaction(db.Model):
    __table_args__ = (
        db.CheckConstraint("amount_minor > 0 AND amount_minor <= 99999999999"),
        db.CheckConstraint("kind IN ('expense', 'income')"),
        db.UniqueConstraint("recurring_id", "occurrence_date", name="unique_recurring_occurrence"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    amount_minor = db.Column(db.BigInteger, nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    payment_method = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(500), nullable=False, default="")
    recurring_id = db.Column(db.Integer, db.ForeignKey("recurring_expense.id"))
    occurrence_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    category = db.relationship("Category")


class Budget(db.Model):
    __table_args__ = (
        db.UniqueConstraint("user_id", "category_id", "month"),
        db.CheckConstraint("amount_minor > 0"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    month = db.Column(db.Date, nullable=False)  # Always day 1.
    amount_minor = db.Column(db.BigInteger, nullable=False)
    category = db.relationship("Category")


class RecurringExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    amount_minor = db.Column(db.BigInteger, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(500), nullable=False, default="")
    frequency = db.Column(db.String(10), nullable=False)  # weekly, monthly, yearly
    next_due = db.Column(db.Date, nullable=False)
    anchor_day = db.Column(db.Integer, nullable=False)  # Jan 31 -> Feb 28 -> Mar 31
    active = db.Column(db.Boolean, nullable=False, default=True)
    category = db.relationship("Category")


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    event = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
