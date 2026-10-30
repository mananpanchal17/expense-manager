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
