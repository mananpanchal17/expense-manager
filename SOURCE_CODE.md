# Expense Manager — complete source code

## Folder structure

```text
expense_manager/
├── app/
│   ├── __init__.py             # Application factory, errors, CLI commands
│   ├── extensions.py           # Shared database, login, CSRF, rate limiter
│   ├── models.py               # Six database tables
│   ├── forms.py                # Server-side form validation
│   ├── services.py             # Reusable business logic
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py           # Accounts, sessions, password reset, profile
│   ├── expenses/
│   │   ├── __init__.py
│   │   └── routes.py           # Transactions, categories, budgets, recurring, import
│   ├── reports/
│   │   ├── __init__.py
│   │   └── routes.py           # Dashboard, chart JSON, reports, CSV/PDF export
│   ├── templates/
│   │   ├── base.html
│   │   ├── macros.html
│   │   ├── auth/{form,profile}.html
│   │   ├── expenses/{form,index,categories,budgets,recurring,import}.html
│   │   ├── reports/{dashboard,report}.html
│   │   └── errors/error.html
│   └── static/
│       ├── css/style.css
│       ├── js/{theme,app,charts}.js
│       └── fonts/{DejaVuSans.ttf,LICENSE-DejaVu.txt}
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_expenses.py
│   └── test_security.py
├── .vscode/                   # One-click VS Code setup, run and test tasks
├── config.py
├── run.py
├── setup_windows.bat          # First-time Windows setup
├── run_windows.bat            # Windows launcher
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── sample_transactions.csv
├── README.md
├── SCHEMA.md
├── VALIDATION.md
└── SOURCE_CODE.md
```

Every text source file is reproduced below. See README.md for file-by-file explanations, setup, deployment and future improvements, SCHEMA.md for the database, and VALIDATION.md for test results. DejaVuSans.ttf is a binary font included in the ZIP with its license.

## `run.py`

```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()  # Debug is deliberately off; Flask CLI can enable it locally.

```

## `setup_windows.bat`

```bat
@echo off
setlocal
cd /d "%~dp0"

echo.
echo ========================================
echo   Expense Manager - First-time setup
echo ========================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python Launcher was not found.
    echo Install Python 3.12 from https://www.python.org/downloads/
    echo During installation, tick "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating the Python environment...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Python 3.12 was not found. Trying your default Python 3...
        py -3 -m venv .venv
    )
    if errorlevel 1 goto :failed
) else (
    echo [1/4] Python environment already exists.
)

echo [2/4] Installing required packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [3/4] Preparing local settings...
if not exist ".env" copy ".env.example" ".env" >nul
".venv\Scripts\python.exe" -c "from pathlib import Path; import secrets; p=Path('.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('SECRET_KEY=\n', 'SECRET_KEY='+secrets.token_hex(32)+'\n', 1), encoding='utf-8')"
if errorlevel 1 goto :failed

echo [4/4] Creating the database...
".venv\Scripts\python.exe" -m flask --app run init-db
if errorlevel 1 goto :failed

echo.
echo Setup completed successfully.
echo Double-click run_windows.bat to start Expense Manager.
pause
exit /b 0

:failed
echo.
echo Setup failed. Keep this window open and send a screenshot of the error.
pause
exit /b 1
```

## `run_windows.bat`

```bat
@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Expense Manager needs first-time setup.
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

if not exist ".env" (
    echo Local settings are missing. Running setup again...
    call setup_windows.bat
    if errorlevel 1 exit /b 1
)

echo.
echo Starting Expense Manager...
echo Open http://127.0.0.1:5000 in your browser.
echo Keep this window open. Press Ctrl+C to stop the app.
echo.
".venv\Scripts\python.exe" -m flask --app run run --debug

echo.
echo Expense Manager stopped.
pause
```

## `.vscode/tasks.json`

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Expense Manager: First-time setup",
      "type": "shell",
      "command": "${workspaceFolder}\\setup_windows.bat",
      "options": {
        "cwd": "${workspaceFolder}",
        "shell": {
          "executable": "cmd.exe",
          "args": ["/d", "/c"]
        }
      },
      "problemMatcher": []
    },
    {
      "label": "Expense Manager: Run",
      "type": "shell",
      "command": "${workspaceFolder}\\run_windows.bat",
      "options": {
        "cwd": "${workspaceFolder}",
        "shell": {
          "executable": "cmd.exe",
          "args": ["/d", "/c"]
        }
      },
      "problemMatcher": []
    },
    {
      "label": "Expense Manager: Run tests",
      "type": "shell",
      "command": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
      "args": ["-m", "pytest", "-q"],
      "options": {
        "cwd": "${workspaceFolder}"
      },
      "problemMatcher": []
    }
  ]
}
```

## `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run Expense Manager",
      "type": "debugpy",
      "request": "launch",
      "module": "flask",
      "python": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
      "args": ["--app", "run", "run", "--debug"],
      "cwd": "${workspaceFolder}",
      "envFile": "${workspaceFolder}\\.env",
      "jinja": true,
      "justMyCode": true,
      "preLaunchTask": "Expense Manager: First-time setup"
    }
  ]
}
```

## `config.py`

```python
"""Environment-based settings. Real secrets belong in .env, never in Git."""

import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f'sqlite:///{BASE_DIR / "instance" / "expenses.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    RESET_TOKEN_MAX_AGE = 1800  # 30 minutes
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
    MAIL_MODE = os.getenv("MAIL_MODE", "console")
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@example.com")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    PRODUCTION = os.getenv("APP_ENV", "development") == "production"

```

## `app/__init__.py`

```python
"""Application factory: creates isolated apps for development and tests."""

from pathlib import Path
import click
from flask import Flask, render_template
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from config import Config
from .extensions import db, login_manager, csrf, limiter


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if len(app.config["SECRET_KEY"]) < 32:
        raise RuntimeError("Set SECRET_KEY to a random string of at least 32 characters in .env.")
    if app.config["PRODUCTION"]:
        if not app.config["SESSION_COOKIE_SECURE"] or app.config["MAIL_MODE"] != "smtp":
            raise RuntimeError("Production needs COOKIE_SECURE=true and MAIL_MODE=smtp.")
        if app.config["RATELIMIT_STORAGE_URI"].startswith("memory:"):
            raise RuntimeError("Production needs a shared rate-limit backend, e.g. Redis.")
        if not app.config["APP_BASE_URL"].startswith("https://"):
            raise RuntimeError("Production APP_BASE_URL must use HTTPS.")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.refresh_view = "auth.login"
    login_manager.needs_refresh_message = (
        "Please log in again to change sensitive account settings."
    )
    csrf.init_app(app)
    limiter.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(token):
        return db.session.scalar(db.select(User).where(User.session_token == token))

    from .auth.routes import bp as auth_bp
    from .expenses.routes import bp as expenses_bp
    from .reports.routes import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(reports_bp)

    from .forms import BaseForm

    @app.context_processor
    def common_context():
        from .services import today

        # This display-only form must not re-read an invalid/oversized POST body.
        return {"action_form": BaseForm(formdata=None), "today": today()}

    @app.template_filter("money")
    def money(value):
        from decimal import Decimal

        currency = current_user.currency if current_user.is_authenticated else "INR"
        return f"{currency} {Decimal(value or 0) / 100:,.2f}"

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        if current_user.is_authenticated or "/reset/" in __import__("flask").request.path:
            response.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def error_page(code, message):
        return render_template("errors/error.html", code=code, message=message), code

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return error_page(
            400, "The form expired or its security token is missing. Reload the page and try again."
        )

    for code, message in [
        (400, "Invalid request. Check your filters or form data."),
        (404, "We could not find that page or record."),
        (413, "That upload is too large. The maximum is 2 MB."),
        (429, "Too many requests. Please wait before trying again."),
    ]:
        app.register_error_handler(code, lambda error, c=code, m=message: error_page(c, m))

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return error_page(500, "Something went wrong. Please try again later.")

    @app.cli.command("init-db")
    def init_db():
        """Create missing tables (does not migrate existing tables)."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("generate-recurring")
    def generate_recurring():
        """Generate all due recurring transactions; safe to run again."""
        from .services import process_recurring

        count = process_recurring()
        click.echo(f"Created {count} recurring transaction(s).")

    return app

```

## `app/extensions.py`

```python
"""Create extensions once, attach them to each app in create_app()."""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])

```

## `app/models.py`

```python
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

```

## `app/forms.py`

```python
"""Shared server-side validation; browser validation is only a convenience."""

from decimal import Decimal
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SelectField,
    DecimalField,
    DateField,
    TextAreaField,
    SubmitField,
)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError

PAYMENTS = [(x, x) for x in ["Cash", "UPI", "Debit card", "Credit card", "Bank transfer", "Other"]]
CURRENCIES = [(x, x) for x in ["INR", "USD", "EUR", "GBP"]]


def money_valid(form, field):
    value = field.data
    if (
        value is None
        or not value.is_finite()
        or not Decimal("0.01") <= value <= Decimal("999999999.99")
    ):
        raise ValidationError("Enter an amount from 0.01 to 999,999,999.99.")
    if value != value.quantize(Decimal("0.01")):
        raise ValidationError("Use at most two decimal places.")


def plain_text(value):
    # Keep notes as text, not HTML; Jinja escapes them at output time.
    if isinstance(value, str):
        return "".join(c for c in value.strip() if c in "\n\t" or ord(c) >= 32)
    return value


class BaseForm(FlaskForm):
    submit = SubmitField("Save")


class RegisterForm(BaseForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=80)], filters=[plain_text])
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=254)], filters=[plain_text]
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])


class LoginForm(BaseForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=254)], filters=[plain_text]
    )
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    remember = BooleanField("Remember me for 14 days")


class EmailForm(BaseForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=254)], filters=[plain_text]
    )


class ResetForm(BaseForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm = PasswordField(
        "Confirm new password", validators=[DataRequired(), EqualTo("password")]
    )


class ProfileForm(BaseForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=80)], filters=[plain_text])
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(max=254)], filters=[plain_text]
    )
    currency = SelectField("Display currency (does not convert amounts)", choices=CURRENCIES)
    current_password = PasswordField(
        "Current password to confirm changes", validators=[DataRequired(), Length(max=128)]
    )
    password = PasswordField(
        "New password (optional)", validators=[Optional(), Length(min=10, max=128)]
    )
    confirm = PasswordField("Confirm new password", validators=[EqualTo("password")])


class DeleteAccountForm(BaseForm):
    password = PasswordField("Current password", validators=[DataRequired(), Length(max=128)])
    confirmation = StringField("Type DELETE to confirm", validators=[DataRequired()])

    def validate_confirmation(self, field):
        if field.data != "DELETE":
            raise ValidationError("Type DELETE exactly.")


class TransactionForm(BaseForm):
    kind = SelectField("Type", choices=[("expense", "Expense"), ("income", "Income")])
    amount = DecimalField("Amount", validators=[DataRequired(), money_valid])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    date = DateField("Date", validators=[DataRequired()])
    payment_method = SelectField("Payment method", choices=PAYMENTS)
    notes = TextAreaField("Notes", validators=[Length(max=500)], filters=[plain_text])

    def validate_date(self, field):
        if not 1900 <= field.data.year <= 9998:
            raise ValidationError("Use a year between 1900 and 9998.")


class CategoryForm(BaseForm):
    name = StringField(
        "Category name", validators=[DataRequired(), Length(max=60)], filters=[plain_text]
    )


class BudgetForm(BaseForm):
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    month = StringField("Month (YYYY-MM)", validators=[DataRequired()])
    amount = DecimalField("Monthly limit", validators=[DataRequired(), money_valid])

    def validate_month(self, field):
        import re
        from datetime import date

        if not re.fullmatch(r"\d{4}-\d{2}", field.data):
            raise ValidationError("Use YYYY-MM, e.g. 2026-10.")
        try:
            parsed = date.fromisoformat(field.data + "-01")
            if not 1900 <= parsed.year <= 9998:
                raise ValueError()
        except ValueError:
            raise ValidationError("Enter a valid month.")


class RecurringForm(BaseForm):
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    amount = DecimalField("Amount", validators=[DataRequired(), money_valid])
    next_due = DateField("First / next due date", validators=[DataRequired()])
    frequency = SelectField(
        "Repeat", choices=[("weekly", "Weekly"), ("monthly", "Monthly"), ("yearly", "Yearly")]
    )
    payment_method = SelectField("Payment method", choices=PAYMENTS)
    notes = TextAreaField("Notes", validators=[Length(max=500)], filters=[plain_text])
    active = BooleanField("Active", default=True)

    def validate_next_due(self, field):
        from .services import today
        from datetime import timedelta

        if not today() - timedelta(days=366) <= field.data <= today() + timedelta(days=3660):
            raise ValidationError("Use a date within the last year or next 10 years.")


class ImportForm(BaseForm):
    file = FileField(
        "CSV file (maximum 2 MB / 2,000 rows)", validators=[FileRequired(), FileAllowed(["csv"])]
    )

```

## `app/services.py`

```python
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

```

## `.env.example`

```text
# Copy to .env and replace this placeholder with a newly generated secret.
SECRET_KEY=
APP_ENV=development
APP_BASE_URL=http://127.0.0.1:5000
APP_TIMEZONE=Asia/Kolkata
COOKIE_SECURE=false
# Omit DATABASE_URL to use instance/expenses.db in this project.
# DATABASE_URL=sqlite:////absolute/path/to/expenses.db
RATELIMIT_STORAGE_URI=memory://
# console prints reset links to your LOCAL terminal only. Use smtp when deployed.
MAIL_MODE=console
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_FROM=noreply@example.com
MAIL_USE_TLS=true

```

## `.gitignore`

```text
.venv/
.env
instance/
__pycache__/
*.pyc
.pytest_cache/
*.db
!.vscode/

```

## `app/auth/__init__.py`

```python

```

## `app/auth/routes.py`

```python
"""Authentication and profile routes."""

import secrets
from datetime import timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, login_required, current_user, fresh_login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from ..extensions import db, limiter
from ..models import User, Category, ActivityLog, utcnow
from ..forms import (
    RegisterForm,
    LoginForm,
    EmailForm,
    ResetForm,
    ProfileForm,
    DeleteAccountForm,
    BaseForm,
)
from ..services import log_event, send_reset_email, user_from_reset

bp = Blueprint("auth", __name__, url_prefix="/auth")
DUMMY_HASH = generate_password_hash(secrets.token_hex(24))


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("reports.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.flush()
            for name in ["Food", "Travel", "Rent", "Shopping", "Bills", "Salary", "Other"]:
                db.session.add(Category(user_id=user.id, name=name))
            log_event(user.id, "Account registered")
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.email.errors.append(
                "This email cannot be registered. Try logging in or resetting your password."
            )
        else:
            flash("Account created. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template(
        "auth/form.html",
        form=form,
        title="Create your account",
        intro="Start with a clearer picture of your money.",
    )


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.email == form.email.data.lower()))
        valid = check_password_hash(user.password_hash if user else DUMMY_HASH, form.password.data)
        locked = user and user.locked_until and user.locked_until > utcnow()
        if user and valid and not locked:
            user.failed_attempts = 0
            user.locked_until = None
            log_event(user.id, "Login succeeded")
            db.session.commit()
            session.clear()  # Start a new session; do not retain pre-login state.
            session.permanent = True
            session["_remember"] = "clear"  # Remove any old account's remember cookie.
            login_user(user, remember=form.remember.data)
            return redirect(url_for("reports.dashboard"))
        if user:
            if not locked:
                # SQL expression increments avoid lost updates on simultaneous failures.
                expired = user.locked_until is not None and user.locked_until <= utcnow()
                db.session.execute(
                    db.update(User)
                    .where(User.id == user.id)
                    .values(
                        failed_attempts=1 if expired else User.failed_attempts + 1,
                        locked_until=None,
                    )
                )
                db.session.flush()
                db.session.refresh(user)
                if user.failed_attempts >= 5:
                    user.locked_until = utcnow() + timedelta(minutes=15)
            log_event(user.id, "Login rejected (invalid credentials or locked account)")
            db.session.commit()
        flash(
            "Unable to sign in. Check your details; after 5 failures, wait 15 minutes or reset your password.",
            "danger",
        )
    return render_template(
        "auth/form.html", form=form, title="Welcome back", intro="Your money, organised."
    )


@bp.post("/logout")
@login_required
def logout():
    if BaseForm().validate_on_submit():
        log_event(current_user.id, "Logged out")
        db.session.commit()
        session.clear()
        logout_user()
        flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def forgot_password():
    form = EmailForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).where(User.email == form.email.data.lower()))
        if user:
            try:
                send_reset_email(user)
                log_event(user.id, "Password reset requested")
                db.session.commit()
            except Exception:
                db.session.rollback()
                # Do not log tokens, SMTP passwords or raw mail exceptions.
                current_app.logger.error("Password reset email delivery failed.")
        flash(
            "If this account exists, a reset link has been sent. It expires in 30 minutes.", "info"
        )
        return redirect(url_for("auth.login"))
    return render_template(
        "auth/form.html",
        form=form,
        title="Forgot password",
        intro="We will send you a time-limited reset link.",
    )


@bp.route("/reset/<token>", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def reset_password(token):
    user = user_from_reset(token)
    if not user:
        flash("That reset link is invalid, expired, or already used.", "danger")
        return redirect(url_for("auth.forgot_password"))
    form = ResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.failed_attempts = 0
        user.locked_until = None
        log_event(user.id, "Password reset; previous sessions revoked")
        db.session.commit()
        session.clear()
        logout_user()
        flash("Password changed. Log in with your new password.", "success")
        return redirect(url_for("auth.login"))
    return render_template(
        "auth/form.html",
        form=form,
        title="Choose a new password",
        intro="Use at least 10 characters.",
    )


@bp.route("/profile", methods=["GET", "POST"])
@fresh_login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        else:
            email_changed = current_user.email != form.email.data.lower()
            current_user.name = form.name.data
            current_user.email = form.email.data.lower()
            current_user.currency = form.currency.data
            revoke = bool(form.password.data) or email_changed
            if form.password.data:
                current_user.set_password(form.password.data)
            elif email_changed:
                current_user.session_token = secrets.token_hex(32)
            log_event(current_user.id, "Profile updated")
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                form.email.errors.append("This email is already in use.")
            else:
                if revoke:
                    session.clear()
                    logout_user()
                    flash(
                        "Profile saved. Please log in again; previous sessions were revoked.",
                        "success",
                    )
                    return redirect(url_for("auth.login"))
                flash("Profile saved.", "success")
                return redirect(url_for("auth.profile"))
    logs = db.session.scalars(
        db.select(ActivityLog)
        .where(ActivityLog.user_id == current_user.id)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(100)
    ).all()
    return render_template("auth/profile.html", form=form, title="Your profile", logs=logs)


@bp.route("/delete-account", methods=["GET", "POST"])
@fresh_login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        if current_user.check_password(form.password.data):
            user = current_user._get_current_object()
            session.clear()
            logout_user()
            db.session.delete(user)
            db.session.commit()
            flash("Your account and all its data have been deleted.", "success")
            return redirect(url_for("auth.register"))
        form.password.errors.append("Current password is incorrect.")
    return render_template(
        "auth/form.html",
        form=form,
        title="Permanently delete account",
        intro="This removes all transactions, budgets, recurring rules, categories and logs. This cannot be undone.",
    )

```

## `app/expenses/__init__.py`

```python

```

## `app/expenses/routes.py`

```python
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

```

## `app/reports/__init__.py`

```python

```

## `app/reports/routes.py`

```python
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

```

## `app/static/css/style.css`

```css
:root { --accent:#147d64; --bs-primary:#147d64; }
body { background:#f4f7f6; font-family:Inter,system-ui,-apple-system,'Segoe UI',sans-serif; }
[data-bs-theme="dark"] body { background:#101b21; }
.content-shell { max-width:1440px; padding-left:clamp(16px,4vw,56px); padding-right:clamp(16px,4vw,56px); }
.navbar { min-height:76px; }
.navbar-brand { font-size:1.05rem; letter-spacing:-.4px; }
.brand-mark { display:inline-grid; place-items:center; width:34px; height:34px; margin-right:8px; background:var(--accent); color:#fff; border-radius:10px; }
.nav-link { font-size:.875rem; }
.nav-link.active { color:var(--accent)!important; font-weight:700; }
.btn-primary { --bs-btn-bg:#147d64; --bs-btn-border-color:#147d64; --bs-btn-hover-bg:#0d634f; --bs-btn-hover-border-color:#0d634f; --bs-btn-active-bg:#0d634f; --bs-btn-active-border-color:#0d634f; }
.btn-outline-primary { --bs-btn-color:#147d64; --bs-btn-border-color:#147d64; --bs-btn-hover-bg:#147d64; --bs-btn-hover-border-color:#147d64; }
[data-bs-theme="dark"] .btn-outline-primary { --bs-btn-color:#6ddbb8; --bs-btn-border-color:#6ddbb8; }
a { color:#147d64; }
[data-bs-theme="dark"] a { color:#7bdfc2; }
.btn-primary { color:white!important; }
.card { border:1px solid var(--bs-border-color); border-radius:16px; box-shadow:0 3px 16px #163e3004; }
.card-body { padding:1.5rem; }
.eyebrow { font-size:.7rem; font-weight:750; letter-spacing:1.7px; color:var(--accent); }
[data-bs-theme="dark"] .eyebrow { color:#7bdfc2; }
.metric-card { border-top:3px solid #a8b9c3; }
.metric-card.income { border-top-color:#147d64; }
.metric-card.expense { border-top-color:#e0a56b; }
.metric-card.balance { border-top-color:#597fc3; }
.metric-value { font-size:clamp(1.3rem,2.1vw,1.8rem); font-weight:700; letter-spacing:-.7px; overflow-wrap:anywhere; }
.chart-wrap { height:260px; position:relative; }
.empty-block { padding:3rem 1rem; }
.table th { font-size:.73rem; text-transform:uppercase; letter-spacing:.7px; color:var(--bs-secondary-color); padding:14px; }
.table td { padding:15px 14px; font-size:.875rem; }
.note-text { overflow-wrap:anywhere; white-space:pre-wrap; max-width:550px; }
.auth-layout { max-width:480px; padding-top:2rem; padding-bottom:3rem; }
.form-layout { max-width:700px; }
.form-label { font-size:.875rem; font-weight:600; }
.form-control,.form-select { min-height:42px; }
.budget-progress { width:100%; height:8px; border:0; border-radius:8px; appearance:none; background:var(--bs-secondary-bg); color:#147d64; }
.budget-progress::-webkit-progress-bar { background:var(--bs-secondary-bg); border-radius:8px; }
.budget-progress::-webkit-progress-value { background:#147d64; border-radius:8px; }
.budget-progress::-moz-progress-bar { background:#147d64; border-radius:8px; }
.budget-progress.warning::-webkit-progress-value { background:#d89928; }
.budget-progress.danger::-webkit-progress-value { background:#d54c55; }
.budget-progress.warning::-moz-progress-bar { background:#d89928; }
.budget-progress.danger::-moz-progress-bar { background:#d54c55; }
@media(max-width:575px) { .card-body { padding:1rem; } .navbar-brand { font-size:.95rem; } .chart-wrap { height:230px; } }

```

## `app/static/fonts/LICENSE-DejaVu.txt`

```text
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: DejaVu fonts
Upstream-Author: Stepan Roh <src@users.sourceforge.net> (original author),
                  see /usr/share/doc/fonts-dejavu-core/AUTHORS for full list
Source: https://dejavu-fonts.github.io/

Files: *
Copyright: Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved. 
 Bitstream Vera is a trademark of Bitstream, Inc.
 DejaVu changes are in public domain.
License: bitstream-vera
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of the fonts accompanying this license ("Fonts") and associated
 documentation files (the "Font Software"), to reproduce and distribute the
 Font Software, including without limitation the rights to use, copy, merge,
 publish, distribute, and/or sell copies of the Font Software, and to permit
 persons to whom the Font Software is furnished to do so, subject to the
 following conditions:
 .
 The above copyright and trademark notices and this permission notice shall
 be included in all copies of one or more of the Font Software typefaces.
 .
 The Font Software may be modified, altered, or added to, and in particular
 the designs of glyphs or characters in the Fonts may be modified and
 additional glyphs or characters may be added to the Fonts, only if the fonts
 are renamed to names not containing either the words "Bitstream" or the word
 "Vera".
 .
 This License becomes null and void to the extent applicable to Fonts or Font
 Software that has been modified and is distributed under the "Bitstream
 Vera" names.
 .
 The Font Software may be sold as part of a larger software package but no
 copy of one or more of the Font Software typefaces may be sold by itself.
 .
 THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF COPYRIGHT, PATENT,
 TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL BITSTREAM OR THE GNOME
 FOUNDATION BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, INCLUDING
 ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES,
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
 THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM OTHER DEALINGS IN THE
 FONT SOFTWARE.
 .
 Except as contained in this notice, the names of Gnome, the Gnome
 Foundation, and Bitstream Inc., shall not be used in advertising or
 otherwise to promote the sale, use or other dealings in this Font Software
 without prior written authorization from the Gnome Foundation or Bitstream
 Inc., respectively. For further information, contact: fonts at gnome dot
 org.

Files: debian/*
Copyright: (C) 2005-2006 Peter Cernak <pce@users.sourceforge.net> 
           (C) 2006-2011 Davide Viti <zinosat@tiscali.it>
           (C) 2011-2013 Christian Perrier <bubulle@debian.org>
           (C) 2013 Fabian Greffrath <fabian+debian@greffrath.com>
License: GPL-2+
 This program is free software; you can redistribute it
 and/or modify it under the terms of the GNU General Public
 License as published by the Free Software Foundation; either
 version 2 of the License, or (at your option) any later
 version.
 .
 This program is distributed in the hope that it will be
 useful, but WITHOUT ANY WARRANTY; without even the implied
 warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
 PURPOSE.  See the GNU General Public License for more
 details.
 .
 You should have received a copy of the GNU General Public
 License along with this package; if not, write to the Free
 Software Foundation, Inc., 51 Franklin St, Fifth Floor,
 Boston, MA  02110-1301 USA
 .
 On Debian systems, the full text of the GNU General Public
 License version 2 can be found in the file
 /usr/share/common-licenses/GPL-2'.

```

## `app/static/js/app.js`

```javascript
const toggle = document.getElementById('theme-toggle');
function updateToggle() {
  const dark = document.documentElement.dataset.bsTheme === 'dark';
  toggle.textContent = dark ? 'Light mode' : 'Dark mode';
  toggle.setAttribute('aria-pressed', String(dark));
}
if (toggle) {
  updateToggle();
  toggle.addEventListener('click', () => {
    const theme = document.documentElement.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.bsTheme = theme;
    try { localStorage.setItem('expense-theme', theme); } catch (_) {}
    updateToggle();
    window.dispatchEvent(new Event('themechange'));
  });
}
// Confirmation is a convenience. Authorization and CSRF are enforced in Python.
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

```

## `app/static/js/charts.js`

```javascript
// Fetch JSON rather than inserting user-controlled text into executable scripts.
(async () => {
  const charts = [];
  const palette = ['#147d64','#769ee4','#e5b077','#b78cc6','#e2858d','#64b5bf','#a4b677'];
  try {
    if (typeof Chart === 'undefined') throw new Error('Chart library unavailable');
    const response = await fetch('/reports/chart-data', {headers: {'Accept':'application/json'}});
    if (!response.ok) throw new Error('Chart data unavailable');
    const data = await response.json();
    const money = new Intl.NumberFormat(undefined, {style:'currency',currency:data.currency});
    const options = () => ({responsive:true, maintainAspectRatio:false,
      plugins:{legend:{position:'bottom'},tooltip:{callbacks:{label:ctx => `${ctx.dataset.label || ctx.label}: ${money.format(typeof ctx.parsed === 'number' ? ctx.parsed : ctx.parsed.y)}`}}}});
    charts.push(new Chart(document.getElementById('category-chart'), {
      type:'pie', data:{labels:data.category_labels,datasets:[{data:data.category_values,backgroundColor:palette,borderWidth:2}]}, options:options()
    }));
    if (!data.category_values.length) document.getElementById('category-empty').classList.remove('d-none');
    charts.push(new Chart(document.getElementById('trend-chart'), {
      type:'line', data:{labels:data.labels,datasets:[{label:'Expenses',data:data.expense,borderColor:'#147d64',backgroundColor:'rgba(20,125,100,0.12)',fill:true,tension:.3}]},
      options:{...options(),scales:{y:{beginAtZero:true}}}
    }));
    charts.push(new Chart(document.getElementById('comparison-chart'), {
      type:'bar', data:{labels:data.labels,datasets:[{label:'Income',data:data.income,backgroundColor:'#147d64',borderRadius:4},{label:'Expenses',data:data.expense,backgroundColor:'#e5b077',borderRadius:4}]},
      options:{...options(),scales:{y:{beginAtZero:true}}}
    }));
    function recolor() {
      const color = document.documentElement.dataset.bsTheme === 'dark' ? '#cbd5e1' : '#536472';
      charts.forEach(chart => {
        chart.options.plugins.legend.labels = {color};
        if (chart.config.type !== 'pie') {
          for (const axis of ['x','y']) {
            chart.options.scales[axis] = {...chart.options.scales[axis],ticks:{color},grid:{color:'rgba(128,128,128,.12)'}};
          }
        }
        chart.update();
      });
    }
    recolor(); window.addEventListener('themechange', recolor);
  } catch (_) { document.getElementById('chart-error').classList.remove('d-none'); }
})();

```

## `app/static/js/theme.js`

```javascript
// Apply the saved theme before the page paints. Storage may be unavailable.
(() => {
  let theme = 'light';
  try { theme = localStorage.getItem('expense-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'); } catch (_) {}
  document.documentElement.dataset.bsTheme = theme === 'dark' ? 'dark' : 'light';
})();

```

## `app/templates/auth/form.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form %}
{% block content %}
  <div class="auth-layout mx-auto">
    <div class="eyebrow mb-2">MONEY MADE SIMPLE</div>
    <h1 class="h2 fw-bold">{{ title }}</h1>
    <p class="text-body-secondary mb-4">{{ intro }}</p>
    <div class="card">
      <div class="card-body p-4">{{ render_form(form, 'Create account' if request.endpoint == 'auth.register' else 'Log in' if request.endpoint == 'auth.login' else 'Delete my account permanently' if request.endpoint == 'auth.delete_account' else 'Continue') }}</div>
    </div>
    <div class="mt-3 d-flex justify-content-between gap-3 flex-wrap">
      <a href="{{ url_for('auth.register') }}">Create account</a>
      <a href="{{ url_for('auth.login') }}">Log in</a>
      <a href="{{ url_for('auth.forgot_password') }}">Forgot password?</a>
    </div>
  </div>
{% endblock %}

```

## `app/templates/auth/profile.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form %}
{% block content %}
  <h1 class="h2 fw-bold mb-4">Your profile</h1>
  <div class="row g-4">
    <div class="col-lg-5">
      <div class="card">
        <div class="card-body p-4">{{ render_form(form, 'Update profile') }}</div>
      </div>
      <p class="small text-body-secondary mt-3">Currency is a display preference for this single-currency ledger. Changing it does not convert stored amounts.</p>
      <a href="{{ url_for('auth.delete_account') }}"
         class="btn btn-outline-danger">Delete account</a>
    </div>
    <div class="col-lg-7">
      <div class="card">
        <div class="card-body">
          <h2 class="h5">Recent activity</h2>
          <p class="small text-body-secondary">Latest 100 events · timestamps in UTC</p>
          <div class="table-responsive">
            <table class="table">
              <thead>
                <tr>
                  <th>Time (UTC)</th>
                  <th>Event</th>
                </tr>
              </thead>
              <tbody>
                {% for log in logs %}
                  <tr>
                    <td class="text-nowrap small">{{ log.created_at.strftime("%Y-%m-%d %H:%M") }}</td>
                    <td>{{ log.event }}</td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
{% endblock %}

```

## `app/templates/base.html`

```html
<!DOCTYPE html>
<html lang="en" data-bs-theme="light">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title|default("Expense Manager") }} · Expense Manager</title>
    <script src="{{ url_for('static', filename='js/theme.js') }}"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
          rel="stylesheet">
    <link href="{{ url_for('static', filename='css/style.css') }}"
          rel="stylesheet">
  </head>
  <body>
    <a class="visually-hidden-focusable" href="#main">Skip to content</a>
    <nav class="navbar navbar-expand-lg border-bottom bg-body sticky-top">
      <div class="container-fluid px-lg-4">
        <a class="navbar-brand fw-bold"
           href="{{ url_for('reports.dashboard') }}">
          <span class="brand-mark">E</span> Expense Manager</a>
        <button class="navbar-toggler"
                type="button"
                data-bs-toggle="collapse"
                data-bs-target="#navigation"
                aria-controls="navigation"
                aria-expanded="false"
                aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navigation">
          {% if current_user.is_authenticated %}
            <ul class="navbar-nav me-auto">
              {% for endpoint, label in [('reports.dashboard','Overview'),('expenses.index','Transactions'),('expenses.budgets','Budgets'),('expenses.recurring','Recurring'),('expenses.categories','Categories')] %}
                <li class="nav-item">
                  <a class="nav-link {{ 'active' if request.endpoint == endpoint else '' }}"
                     href="{{ url_for(endpoint) }}">{{ label }}</a>
                </li>
              {% endfor %}
              <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle"
                   href="#"
                   role="button"
                   data-bs-toggle="dropdown"
                   aria-expanded="false">Reports</a>
                <ul class="dropdown-menu">
                  <li>
                    <a class="dropdown-item"
                       href="{{ url_for('reports.report', period='monthly') }}">Monthly report</a>
                  </li>
                  <li>
                    <a class="dropdown-item"
                       href="{{ url_for('reports.report', period='yearly') }}">Yearly report</a>
                  </li>
                </ul>
              </li>
            </ul>
          {% endif %}
          <div class="d-flex gap-2 align-items-center ms-auto flex-wrap py-2">
            <button id="theme-toggle"
                    class="btn btn-sm btn-outline-secondary"
                    type="button"
                    aria-label="Toggle dark mode"
                    aria-pressed="false">Dark mode</button>
            {% if current_user.is_authenticated %}
              <a class="btn btn-sm btn-light" href="{{ url_for('auth.profile') }}">{{ current_user.name }}</a>
              <form method="post" action="{{ url_for('auth.logout') }}">
                {{ action_form.hidden_tag() }}<button class="btn btn-sm btn-outline-secondary">Log out</button>
              </form>
            {% else %}
              <a class="btn btn-sm btn-primary" href="{{ url_for('auth.login') }}">Log in</a>
            {% endif %}
          </div>
        </div>
      </div>
    </nav>
    <main id="main" class="container-fluid content-shell py-4 py-lg-5">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category if category in ['success','warning','danger','info'] else 'info' }} alert-dismissible fade show"
               role="alert">
            {{ message }}<button class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        {% endfor %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>
    <footer class="container-fluid content-shell pb-4 small text-body-secondary">
      Expense Manager · A little clarity, every day.
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="{{ url_for('static', filename='js/app.js') }}" defer></script>
    {% block scripts %}{% endblock %}
  </body>
</html>

```

## `app/templates/errors/error.html`

```html
{% extends "base.html" %}
{% block content %}
  <div class="text-center py-5">
    <div class="display-1 fw-bold text-primary">{{ code }}</div>
    <h1 class="h3 mt-3">{{ message }}</h1>
    <a class="btn btn-primary mt-4"
       href="{{ url_for('reports.dashboard') }}">Back to overview</a>
  </div>
{% endblock %}

```

## `app/templates/expenses/budgets.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form, delete_button %}
{% block content %}
  <div class="d-flex justify-content-between flex-wrap gap-3 mb-4">
    <div>
      <div class="eyebrow">SPEND WITH INTENTION</div>
      <h1 class="h2 fw-bold">Monthly budgets</h1>
    </div>
    <form method="get" class="d-flex gap-2 align-items-center">
      <label for="viewmonth" class="visually-hidden">Month to view</label>
      <input class="form-control"
             type="month"
             name="month"
             id="viewmonth"
             value="{{ month.strftime('%Y-%m') }}">
      <button class="btn btn-outline-secondary">View</button>
    </form>
  </div>
  <div class="row g-4">
    <div class="col-lg-4">
      <div class="card">
        <div class="card-body p-4">
          <h2 class="h5">Set a monthly limit</h2>
          <p class="small text-body-secondary">Use the same category and month to update an existing budget.</p>
          {{ render_form(form, 'Save budget') }}
        </div>
      </div>
    </div>
    <div class="col-lg-8">
      <h2 class="h5 mb-3">{{ month.strftime("%B %Y") }}</h2>
      {% for item in items %}
        <div class="card mb-3">
          <div class="card-body">
            <div class="d-flex justify-content-between mb-2">
              <strong>{{ item.budget.category.name }}</strong>{{ delete_button(url_for('expenses.delete_budget', record_id=item.budget.id)) }}
            </div>
            <div class="d-flex justify-content-between gap-3 mb-2">
              <span>{{ item.spent|money }} <span class="text-body-secondary">of {{ item.budget.amount_minor|money }}</span>
              </span>
              <span class="badge text-bg-{{ item.level }}">{{ item.percent|round(1) }}%</span>
            </div>
            <progress class="budget-progress {{ item.level }}"
                      max="100"
                      value="{{ [item.percent,100]|min }}"
                      aria-label="{{ item.budget.category.name }} budget used">{{ item.percent }}%</progress>
            {% if item.percent >= 100 %}
              <p class="small text-danger mt-2 mb-0">Budget reached or exceeded.</p>
            {% elif item.percent >= 80 %}
              <p class="small mt-2 mb-0">You've used at least 80% of this budget.</p>
            {% endif %}
          </div>
        </div>
      {% else %}
        <div class="card">
          <div class="card-body py-5 text-center text-body-secondary">No budgets for this month. Set your first category limit.</div>
        </div>
      {% endfor %}
    </div>
  </div>
{% endblock %}

```

## `app/templates/expenses/categories.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form, delete_button %}
{% block content %}
  <h1 class="h2 fw-bold mb-4">Categories</h1>
  <div class="row g-4">
    <div class="col-lg-4">
      <section class="card">
        <div class="card-body p-4">
          <h2 class="h5 mb-3">Add a category</h2>
          {{ render_form(form, 'Add category') }}
        </div>
      </section>
    </div>
    <div class="col-lg-8">
      <div class="card">
        <div class="card-body">
          <p class="small text-body-secondary">Categories can be used for income or expenses. In-use categories cannot be deleted.</p>
          <ul class="list-group list-group-flush">
            {% for id,name in categories %}
              <li class="list-group-item d-flex justify-content-between align-items-center gap-2">
                <span>{{ name }}</span>
                <div class="text-nowrap">
                  <a class="btn btn-sm btn-outline-secondary"
                     href="{{ url_for('expenses.edit_category', record_id=id) }}">Edit</a> {{ delete_button(url_for('expenses.delete_category', record_id=id)) }}
                </div>
              </li>
            {% else %}
              <li class="list-group-item">Create a category to start tracking.</li>
            {% endfor %}
          </ul>
        </div>
      </div>
    </div>
  </div>
{% endblock %}

```

## `app/templates/expenses/form.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form %}
{% block content %}
  <div class="form-layout mx-auto">
    <a href="{{ url_for('expenses.index') }}" class="small">← Transactions</a>
    <h1 class="h2 fw-bold mt-3 mb-4">{{ title }}</h1>
    <div class="card">
      <div class="card-body p-4">{{ render_form(form) }}</div>
    </div>
  </div>
{% endblock %}

```

## `app/templates/expenses/import.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form %}
{% block content %}
  <div class="form-layout mx-auto">
    <h1 class="h2 fw-bold mb-4">Import transactions</h1>
    <div class="card">
      <div class="card-body p-4">
        <p>Upload a UTF-8 CSV with these exact headers. Both income and expenses are supported. Create any missing categories first.</p>
        <pre class="small p-3 bg-body-tertiary rounded">kind,amount,category,date,payment_method,notes
expense,120.50,Food,2026-10-30,UPI,Lunch
income,5000.00,Salary,2026-10-30,Bank transfer,Allowance</pre>
        <p class="small text-body-secondary">Dates: YYYY-MM-DD. Amounts: positive, with at most two decimal places. Payment methods: Cash, UPI, Debit card, Credit card, Bank transfer, Other.</p>
        <div class="alert alert-info">Every row must be valid, or nothing is imported. Re-importing the same file creates duplicate transactions.</div>
        {{ render_form(form, 'Validate and import', true) }}
      </div>
    </div>
  </div>
{% endblock %}

```

## `app/templates/expenses/index.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import transaction_table %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">
    <div>
      <div class="eyebrow">YOUR LEDGER</div>
      <h1 class="h2 fw-bold mb-0">Transactions</h1>
    </div>
    <div class="d-flex flex-wrap gap-2">
      <a class="btn btn-outline-secondary"
         href="{{ url_for('expenses.import_csv') }}">Import CSV</a>
      <a class="btn btn-outline-secondary"
         href="{{ url_for('reports.export_csv', **request.args) }}">Export CSV</a>
      <a class="btn btn-outline-secondary"
         href="{{ url_for('reports.export_pdf', **request.args) }}">Export PDF</a>
      <a class="btn btn-primary" href="{{ url_for('expenses.add') }}">+ Add transaction</a>
    </div>
  </div>
  <div class="card mb-4">
    <div class="card-body">
      <form method="get" class="row g-3 align-items-end">
        <div class="col-md-4">
          <label class="form-label" for="q">Search notes or categories</label>
          <input class="form-control"
                 name="q"
                 id="q"
                 value="{{ request.args.get('q', '') }}"
                 maxlength="100"
                 placeholder="Coffee, travel, rent…">
        </div>
        <div class="col-6 col-md-2">
          <label for="kind" class="form-label">Type</label>
          <select name="kind" id="kind" class="form-select">
            <option value="">All types</option>
            {% for val in ['income','expense'] %}
              <option value="{{ val }}" {{ 'selected' if request.args.get("kind") == val }}>{{ val|title }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-6 col-md-3">
          <label for="category" class="form-label">Category</label>
          <select name="category" id="category" class="form-select">
            <option value="">All categories</option>
            {% for id,name in categories %}
              <option value="{{ id }}"
                      {{ 'selected' if request.args.get("category") == id|string }}>{{ name }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-3">
          <label for="sort" class="form-label">Sort</label>
          <select class="form-select" id="sort" name="sort">
            {% for val,label in [('date_desc','Newest first'),('date_asc','Oldest first'),('amount_desc','Highest amount'),('amount_asc','Lowest amount'),('category','Category A–Z')] %}
              <option value="{{ val }}"
                      {{ 'selected' if request.args.get('sort', 'date_desc') == val }}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        {% for name,label,type in [('start','From date','date'),('end','To date','date'),('min_amount','Minimum amount','number'),('max_amount','Maximum amount','number')] %}
          <div class="col-6 col-md-2">
            <label class="form-label" for="{{ name }}">{{ label }}</label>
            <input type="{{ type }}"
                   {% if type == 'number' %}step="0.01" min="0"{% endif %}
                   class="form-control"
                   id="{{ name }}"
                   name="{{ name }}"
                   value="{{ request.args.get(name,'') }}">
          </div>
        {% endfor %}
        <div class="col-md-4 d-flex gap-2">
          <button class="btn btn-primary">Apply filters</button>
          <a href="{{ url_for('expenses.index') }}"
             class="btn btn-outline-secondary">Clear</a>
        </div>
      </form>
    </div>
  </div>
  <div class="card overflow-hidden">{{ transaction_table(page.items, true) }}</div>
  <div class="d-flex justify-content-between align-items-center mt-3">
    <span class="small text-body-secondary">{{ page.total }} records · Page {{ page.page }} of {{ page.pages or 1 }}</span>
    <div class="d-flex gap-2">
      {% if page.has_prev %}
        <a class="btn btn-outline-secondary btn-sm"
           href="{{ url_for('expenses.index', **dict(request.args, page=page.prev_num)) }}">Previous</a>
      {% endif %}
      {% if page.has_next %}
        <a class="btn btn-outline-secondary btn-sm"
           href="{{ url_for('expenses.index', **dict(request.args, page=page.next_num)) }}">Next</a>
      {% endif %}
    </div>
  </div>
{% endblock %}

```

## `app/templates/expenses/recurring.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import render_form, delete_button %}
{% block content %}
  <div class="d-flex justify-content-between flex-wrap gap-3 mb-4">
    <div>
      <div class="eyebrow">PLAN AHEAD</div>
      <h1 class="h2 fw-bold">Recurring expenses</h1>
    </div>
    <form method="post" action="{{ url_for('expenses.generate_recurring') }}">
      {{ action_form.hidden_tag() }}<button class="btn btn-primary">Generate due expenses</button>
    </form>
  </div>
  <p class="text-body-secondary">Create rules for rent and subscriptions. Generate overdue entries here or run the daily scheduled command described in the README.</p>
  <div class="row g-4">
    <div class="col-lg-4">
      <div class="card">
        <div class="card-body p-4">
          <h2 class="h5 mb-3">New recurring expense</h2>
          {{ render_form(form, 'Create rule') }}
        </div>
      </div>
    </div>
    <div class="col-lg-8">
      {% for rule in rules %}
        <div class="card mb-3">
          <div class="card-body">
            <div class="d-flex justify-content-between gap-3">
              <h2 class="h5">{{ rule.category.name }}</h2>
              <strong>{{ rule.amount_minor|money }}</strong>
            </div>
            <p class="text-body-secondary mb-2">{{ rule.frequency|title }} · Next due {{ rule.next_due }} · {{ rule.payment_method }}</p>
            <p class="note-text">{{ rule.notes }}</p>
            <div class="d-flex align-items-center gap-2">
              <span class="badge {{ 'text-bg-success' if rule.active else 'text-bg-secondary' }} me-auto">{{ 'Active' if rule.active else 'Paused' }}</span>
              <a class="btn btn-sm btn-outline-secondary"
                 href="{{ url_for('expenses.edit_recurring', record_id=rule.id) }}">Edit / pause</a>{{ delete_button(url_for('expenses.delete_recurring', record_id=rule.id), 'Delete this rule? Previously generated transactions will remain.') }}
            </div>
          </div>
        </div>
      {% else %}
        <div class="card">
          <div class="card-body py-5 text-center text-body-secondary">No recurring rules yet.</div>
        </div>
      {% endfor %}
    </div>
  </div>
{% endblock %}

```

## `app/templates/macros.html`

```html
{% macro render_form(form, button='Save', multipart=false) %}
  <form method="post"
        {% if multipart %}enctype="multipart/form-data"{% endif %}>
    {{ form.hidden_tag() }}
    {% for field in form if field.type not in ['CSRFTokenField','HiddenField','SubmitField'] %}
      <div class="mb-3">
        {% if field.type == "BooleanField" %}
          <div class="form-check">{{ field(class='form-check-input') }}{{ field.label(class='form-check-label') }}</div>
        {% else %}
          {{ field.label(class='form-label') }}
          {% if field.type == "SelectField" %}{{ field(class='form-select' + (' is-invalid' if field.errors else '')) }}
          {% elif field.type == "DecimalField" %}{{ field(class='form-control' + (' is-invalid' if field.errors else ''), step='0.01', min='0.01', max='999999999.99') }}
          {% elif field.type == "PasswordField" %}{{ field(class='form-control' + (' is-invalid' if field.errors else ''), autocomplete='current-password' if field.name in ['current_password','password'] and request.endpoint in ['auth.login','auth.profile','auth.delete_account'] else 'new-password') }}
        {% else %}{{ field(class='form-control' + (' is-invalid' if field.errors else '')) }}{% endif %}
      {% endif %}
      {% for error in field.errors %}
        <div class="text-danger small mt-1">{{ error }}</div>
      {% endfor %}
      </div>
    {% endfor %}
    <button class="btn btn-primary px-4" type="submit">{{ button }}</button>
  </form>
{% endmacro %}
{% macro delete_button(action, message='Delete this record?') %}
  <form method="post"
        action="{{ action }}"
        class="d-inline"
        data-confirm="{{ message }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button class="btn btn-sm btn-outline-danger" type="submit">Delete</button>
  </form>
{% endmacro %}
{% macro summary_cards(summary, month_spend=none) %}
  <div class="row g-3 mb-4">
    {% for label, value, color in [('Total income', summary.income,'income'),('Total expenses',summary.expense,'expense'),('Balance',summary.balance,'balance')] %}
      <div class="col-sm-6 {{ 'col-xl-3' if month_spend is not none else 'col-lg-4' }}">
        <section class="card metric-card h-100 {{ color }}">
          <div class="card-body">
            <p class="text-body-secondary small mb-2">{{ label }}</p>
            <p class="metric-value mb-0">{{ value|money }}</p>
          </div>
        </section>
      </div>
    {% endfor %}
    {% if month_spend is not none %}
      <div class="col-sm-6 col-xl-3">
        <section class="card metric-card h-100">
          <div class="card-body">
            <p class="text-body-secondary small mb-2">This month's spend</p>
            <p class="metric-value mb-0">{{ month_spend|money }}</p>
          </div>
        </section>
      </div>
    {% endif %}
  </div>
{% endmacro %}
{% macro transaction_table(rows, editable=false) %}
  <div class="table-responsive">
    <table class="table align-middle mb-0">
      <thead>
        <tr>
          <th>Date</th>
          <th>Category / notes</th>
          <th>Payment</th>
          <th>Type</th>
          <th class="text-end">Amount</th>
          {% if editable %}
            <th class="text-end">Actions</th>
          {% endif %}
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
          <tr>
            <td class="text-nowrap">{{ row.date }}</td>
            <td>
              <div class="fw-semibold">{{ row.category.name }}</div>
              <div class="small text-body-secondary note-text">{{ row.notes }}{% if row.recurring_id %} <span class="badge text-bg-secondary">Recurring</span>
        {% endif %}
      </div>
    </td>
    <td>{{ row.payment_method }}</td>
    <td>
      <span class="badge {{ 'text-bg-success' if row.kind == 'income' else 'text-bg-light' }}">{{ row.kind|title }}</span>
    </td>
    <td class="text-end text-nowrap fw-semibold">{{ row.amount_minor|money }}</td>
    {% if editable %}
      <td class="text-end text-nowrap">
        <a class="btn btn-sm btn-outline-secondary"
           href="{{ url_for('expenses.edit', record_id=row.id) }}">Edit</a> {{ delete_button(url_for('expenses.delete', record_id=row.id)) }}
      </td>
    {% endif %}
  </tr>
{% else %}
  <tr>
    <td colspan="{{ 6 if editable else 5 }}"
        class="text-center py-5 text-body-secondary">No transactions yet. Add your first income or expense to get started.</td>
  </tr>
{% endfor %}
</tbody>
</table>
</div>
{% endmacro %}

```

## `app/templates/reports/dashboard.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import summary_cards, transaction_table %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center flex-wrap gap-3 mb-4">
    <div>
      <div class="eyebrow mb-1">{{ today.strftime("%B %Y") }} · YOUR MONEY AT A GLANCE</div>
      <h1 class="fw-bold h2 mb-1">A clearer picture.</h1>
      <p class="text-body-secondary mb-0">Welcome, {{ current_user.name }}. Here's where things stand.</p>
    </div>
    <a class="btn btn-primary" href="{{ url_for('expenses.add') }}">+ Add transaction</a>
  </div>
  {{ summary_cards(summary, month_spend) }}
  {% for item in budgets if item.percent >= 80 %}
    <div class="alert alert-{{ item.level }}">
      {{ item.budget.category.name }}: {{ item.percent|round(1) }}% of this month's budget used. <a class="alert-link"
    href="{{ url_for('expenses.budgets') }}">Review budgets</a>
    </div>
  {% endfor %}
  <div id="chart-error"
       class="alert alert-warning d-none"
       role="status">Charts could not load. Your balances and reports are still available.</div>
  <div class="row g-4 mb-4">
    <div class="col-lg-4">
      <div class="card h-100">
        <div class="card-body">
          <h2 class="h5">Where it went</h2>
          <p class="small text-body-secondary">Expense categories · this month</p>
          <div class="chart-wrap">
            <canvas id="category-chart"
                    role="img"
                    aria-label="Expenses by category for this month">
            </canvas>
          </div>
          <p id="category-empty"
             class="small text-body-secondary d-none">Add an expense this month to see your breakdown.</p>
          <a class="small"
             href="{{ url_for('reports.report', period='monthly') }}">View accessible table</a>
        </div>
      </div>
    </div>
    <div class="col-lg-8">
      <div class="card h-100">
        <div class="card-body">
          <h2 class="h5">Your spending rhythm</h2>
          <p class="small text-body-secondary">Monthly expenses · last 12 months</p>
          <div class="chart-wrap">
            <canvas id="trend-chart"
                    role="img"
                    aria-label="Monthly expense trend over the past 12 months">
            </canvas>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="row g-4 mb-4">
    <div class="col-lg-7">
      <div class="card h-100">
        <div class="card-body">
          <h2 class="h5">In vs out</h2>
          <p class="small text-body-secondary">Income and expenses · last 12 months</p>
          <div class="chart-wrap">
            <canvas id="comparison-chart"
                    role="img"
                    aria-label="Income and expense comparison">
            </canvas>
          </div>
        </div>
      </div>
    </div>
    <div class="col-lg-5">
      <div class="card h-100">
        <div class="card-body">
          <div class="d-flex justify-content-between">
            <h2 class="h5">Budget check-in</h2>
            <a class="small" href="{{ url_for('expenses.budgets') }}">Manage</a>
          </div>
          {% for item in budgets %}
            <div class="mt-4">
              <div class="d-flex justify-content-between small mb-2">
                <strong>{{ item.budget.category.name }}</strong>
                <span>{{ item.percent|round(1) }}%</span>
              </div>
              <progress class="budget-progress {{ item.level }}"
                        max="100"
                        value="{{ [item.percent,100]|min }}"
                        aria-label="{{ item.budget.category.name }} budget used">
              </progress>
              <p class="small text-body-secondary mt-1">{{ item.spent|money }} / {{ item.budget.amount_minor|money }}</p>
            </div>
          {% else %}
            <div class="empty-block">
              <p class="h5">Give your spending a plan.</p>
              <p class="text-body-secondary small">Set monthly category limits and get a warning at 80% and 100%.</p>
              <a class="btn btn-outline-primary"
                 href="{{ url_for('expenses.budgets') }}">Create a budget</a>
            </div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
  <section class="card overflow-hidden">
    <div class="card-body d-flex justify-content-between">
      <h2 class="h5 mb-0">Recent transactions</h2>
      <a class="small" href="{{ url_for('expenses.index') }}">View all →</a>
    </div>
    {{ transaction_table(recent) }}
  </section>
{% endblock %}
{% block scripts %}
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"></script>
  <script src="{{ url_for('static', filename='js/charts.js') }}" defer></script>
{% endblock %}

```

## `app/templates/reports/report.html`

```html
{% extends "base.html" %}
{% from 'macros.html' import summary_cards %}
{% block content %}
  <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap mb-4">
    <div>
      <div class="eyebrow">LOOK BACK, PLAN FORWARD</div>
      <h1 class="h2 fw-bold">{{ title }}</h1>
      <span class="text-body-secondary">{{ start }} to {{ end }}</span>
    </div>
    <div class="d-flex gap-2">
      <a class="btn btn-outline-secondary"
         href="{{ url_for('reports.export_csv', start=start, end=end) }}">Export CSV</a>
      <a class="btn btn-outline-secondary"
         href="{{ url_for('reports.export_pdf', start=start, end=end) }}">Export PDF</a>
    </div>
  </div>
  <form method="get" class="d-flex gap-2 align-items-end mb-4 flex-wrap">
    <div>
      <label for="year" class="form-label">Year</label>
      <input class="form-control"
             type="number"
             min="1900"
             max="9998"
             name="year"
             id="year"
             value="{{ year }}"
             required>
    </div>
    {% if period == "monthly" %}
      <div>
        <label for="month" class="form-label">Month</label>
        <select class="form-select" name="month" id="month">
          {% for m in range(1,13) %}
            <option value="{{ m }}" {{ 'selected' if m == month }}>{{ m }}</option>
          {% endfor %}
        </select>
      </div>
    {% endif %}
    <button class="btn btn-primary">Show report</button>
    <a class="btn btn-outline-secondary"
       href="{{ url_for('reports.report', period='yearly' if period == 'monthly' else 'monthly', year=year) }}">{{ 'Yearly' if period == 'monthly' else 'Monthly' }} report</a>
  </form>
  {{ summary_cards(summary) }}
  {% if month_rows %}
    <div class="card mb-4">
      <div class="card-body">
        <h2 class="h5">Month by month</h2>
        <div class="table-responsive">
          <table class="table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Income</th>
                <th>Expenses</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {% for name,values in month_rows %}
                <tr>
                  <td>{{ name }}</td>
                  <td>{{ values.income|money }}</td>
                  <td>{{ values.expense|money }}</td>
                  <td>{{ values.balance|money }}</td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  {% endif %}
  <div class="card">
    <div class="card-body">
      <h2 class="h5">Category breakdown</h2>
      <div class="table-responsive">
        <table class="table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Type</th>
              <th class="text-end">Total</th>
            </tr>
          </thead>
          <tbody>
            {% for category,kind,amount in rows %}
              <tr>
                <td>{{ category }}</td>
                <td>{{ kind|title }}</td>
                <td class="text-end">{{ amount|money }}</td>
              </tr>
            {% else %}
              <tr>
                <td colspan="3" class="text-center text-body-secondary py-4">No transactions in this period.</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
{% endblock %}

```

## `pytest.ini`

```ini
[pytest]
testpaths = tests
pythonpath = .

```

## `requirements.txt`

```text
blinker==1.9.0
charset-normalizer==3.5.2
click==8.5.0
Deprecated==3.0.1
dnspython==2.9.1
email-validator==2.3.0
Flask==3.1.3
Flask-Limiter==4.1.1
Flask-Login==0.6.3
Flask-SQLAlchemy==3.1.1
Flask-WTF==1.3.0
gunicorn==26.2.0
idna==3.20
iniconfig==2.3.1
itsdangerous==2.2.0
Jinja2==3.1.6
limits==5.8.0
MarkupSafe==3.0.4
ordered-set==4.1.0
packaging==26.3
pillow==13.0.0
pluggy==1.7.0
Pygments==2.21.0
pytest==9.2.0
python-dotenv==1.2.4
redis==7.4.1
reportlab==5.1.0
SQLAlchemy==2.1.6
typing_extensions==4.16.0
tzdata==2026.6
Werkzeug==3.1.9
wrapt==2.5.2
WTForms==3.3.1

```

## `sample_transactions.csv`

```csv
kind,amount,category,date,payment_method,notes
income,15000.00,Salary,2026-10-01,Bank transfer,Monthly allowance
expense,180.00,Food,2026-10-02,UPI,Lunch
expense,350.00,Travel,2026-10-03,Cash,Bus pass
expense,5000.00,Rent,2026-10-05,Bank transfer,Hostel rent
expense,799.00,Bills,2026-10-10,UPI,Phone recharge

```

## `tests/conftest.py`

```python
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

```

## `tests/test_auth.py`

```python
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

```

## `tests/test_expenses.py`

```python
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

```

## `tests/test_security.py`

```python
import re
from app.extensions import db
from app.models import User
from conftest import category_id, transaction_data, register


def test_csrf_required_and_valid_token_accepted(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    assert (
        client.post(
            "/auth/login", data={"email": "x@example.com", "password": "password"}
        ).status_code
        == 400
    )
    page = client.get("/auth/register").data.decode()
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": token,
            "name": "Tester",
            "email": "test@example.com",
            "password": "long-password-123",
            "confirm": "long-password-123",
        },
    )
    assert response.status_code == 302


def test_csrf_on_crud_and_no_get_deletes(signed_in, app):
    cid = category_id(app)
    signed_in.post("/expenses/add", data=transaction_data(cid))
    app.config["WTF_CSRF_ENABLED"] = True
    for path in [
        "/expenses/add",
        "/expenses/1/delete",
        "/auth/logout",
        "/expenses/recurring/generate",
        "/auth/delete-account",
    ]:
        assert signed_in.post(path).status_code == 400
    assert signed_in.get("/expenses/1/delete").status_code == 405


def test_xss_is_escaped_and_headers(signed_in, app):
    cid = category_id(app)
    signed_in.post("/expenses/add", data=transaction_data(cid, notes="<script>alert(1)</script>"))
    response = signed_in.get("/expenses/")
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "object-src 'none'" in response.headers["Content-Security-Policy"]


def test_custom_errors(client):
    response = client.get("/missing-page")
    assert response.status_code == 404 and b"could not find" in response.data


def test_login_rate_limit(tmp_path):
    from app import create_app

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-rate-secret-" * 4,
            "PRODUCTION": False,
            "SQLALCHEMY_DATABASE_URI": f'sqlite:///{tmp_path / "rate.db"}',
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": True,
            "RATELIMIT_STORAGE_URI": "memory://",
        }
    )
    with app.app_context():
        db.create_all()
    client = app.test_client()
    for _ in range(10):
        assert (
            client.post(
                "/auth/login", data={"email": "nobody@example.com", "password": "invalid"}
            ).status_code
            == 200
        )
    assert (
        client.post(
            "/auth/login", data={"email": "nobody@example.com", "password": "invalid"}
        ).status_code
        == 429
    )


def test_custom_500_page_and_oversized_upload(app, client):
    @app.get("/test-error")
    def test_error():
        raise RuntimeError("test-only failure")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = client.get("/test-error")
    assert response.status_code == 500
    assert b"Something went wrong" in response.data
    assert b"RuntimeError" not in response.data
    app.config["MAX_CONTENT_LENGTH"] = 10
    response = client.post(
        "/auth/login", data={"email": "someone@example.com", "password": "a" * 100}
    )
    assert response.status_code == 413


def test_real_csrf_registration_login_and_transaction(app, client):
    app.config["WTF_CSRF_ENABLED"] = True

    def csrf(path):
        page = client.get(path).data.decode()
        return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page).group(1)

    response = client.post(
        "/auth/register",
        data={
            "csrf_token": csrf("/auth/register"),
            "name": "Student",
            "email": "student@example.com",
            "password": "correct-horse-123",
            "confirm": "correct-horse-123",
        },
    )
    assert response.status_code == 302
    response = client.post(
        "/auth/login",
        data={
            "csrf_token": csrf("/auth/login"),
            "email": "student@example.com",
            "password": "correct-horse-123",
        },
    )
    assert response.status_code == 302
    cid = category_id(app)
    data = transaction_data(cid)
    data["csrf_token"] = csrf("/expenses/add")
    assert client.post("/expenses/add", data=data).status_code == 302
    assert b"Lunch" in client.get("/expenses/").data

```

