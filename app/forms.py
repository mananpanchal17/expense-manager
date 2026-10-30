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
