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
