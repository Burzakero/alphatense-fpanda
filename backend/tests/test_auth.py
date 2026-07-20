import uuid
from datetime import timedelta

from fastapi.testclient import TestClient

from app.api.main import app
from app.db import repository
from app.db.database import SessionLocal
from app.db.models import Session as SessionRecord, utcnow

client = TestClient(app)


def _unique_email() -> str:
    return f"advisor-{uuid.uuid4()}@example.com"


def _signup(email: str | None = None, password: str = "correcthorsebattery") -> dict:
    response = client.post(
        "/auth/signup",
        json={"name": "Acme Advisory", "email": email or _unique_email(), "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_signup_returns_token_and_advisor():
    body = _signup()
    assert body["token"]
    assert body["advisor"]["name"] == "Acme Advisory"
    assert "password" not in body["advisor"] and "password_hash" not in body["advisor"]


def test_signup_rejects_duplicate_email():
    email = _unique_email()
    _signup(email=email)
    response = client.post("/auth/signup", json={"name": "Someone Else", "email": email, "password": "whatever123"})
    assert response.status_code == 409


def test_signup_rejects_short_password():
    response = client.post(
        "/auth/signup", json={"name": "Acme", "email": _unique_email(), "password": "short"}
    )
    assert response.status_code == 400


def test_login_with_correct_password():
    email = _unique_email()
    _signup(email=email, password="correcthorsebattery")
    response = client.post("/auth/login", json={"email": email, "password": "correcthorsebattery"})
    assert response.status_code == 200
    assert response.json()["token"]


def test_login_with_wrong_password_returns_401():
    email = _unique_email()
    _signup(email=email, password="correcthorsebattery")
    response = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert response.status_code == 401


def test_login_unknown_email_returns_401():
    response = client.post("/auth/login", json={"email": _unique_email(), "password": "whatever123"})
    assert response.status_code == 401


def test_me_without_token_returns_401():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_with_invalid_token_returns_401():
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_with_expired_token_returns_401():
    body = _signup()
    token = body["token"]

    # Force the freshly-issued session to already be expired.
    db = SessionLocal()
    try:
        token_hash = repository._hash_token(token)
        record = db.get(SessionRecord, token_hash)
        record.expires_at = utcnow() - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_returns_own_workspace_ids():
    body = _signup()
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.get("/auth/me", headers=headers).json()["workspace_ids"] == []


def test_logout_invalidates_token():
    body = _signup()
    headers = {"Authorization": f"Bearer {body['token']}"}
    assert client.get("/auth/me", headers=headers).status_code == 200

    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_advisor_cannot_access_another_advisors_workspace():
    advisor_a = _signup()
    advisor_b = _signup()
    headers_a = {"Authorization": f"Bearer {advisor_a['token']}"}
    headers_b = {"Authorization": f"Bearer {advisor_b['token']}"}

    sample_csv = (
        __import__("pathlib").Path(__file__).resolve().parents[1] / "sample_data" / "sample_financials.csv"
    )
    with open(sample_csv, "rb") as f:
        upload = client.post(
            "/workspaces",
            files={"file": ("sample_financials.csv", f, "text/csv")},
            headers=headers_a,
        )
    assert upload.status_code == 201
    workspace_id = upload.json()["workspace_id"]

    # Owner can see it; a different advisor gets a 404, not a 403 -- the
    # response shouldn't confirm the workspace exists at all to a non-owner.
    assert client.get(f"/workspaces/{workspace_id}/clients", headers=headers_a).status_code == 200
    assert client.get(f"/workspaces/{workspace_id}/clients", headers=headers_b).status_code == 404
