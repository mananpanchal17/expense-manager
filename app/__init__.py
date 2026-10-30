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
