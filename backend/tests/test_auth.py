"""Authentication endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import csrf_headers


def test_register_creates_an_account(client: TestClient, registered_user: dict[str, str]) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == registered_user["email"]
    assert body["full_name"] == "Test Grower"
    assert "password" not in body
    assert "password_hash" not in body


def test_password_is_never_returned_or_stored_in_plain_text(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    response = client.get("/api/auth/me")
    assert registered_user["password"] not in response.text

    from core.database import SessionLocal
    from services import auth_service

    with SessionLocal() as db:
        user = auth_service.get_user_by_email(db, registered_user["email"])
        assert user is not None
        assert user.password_hash != registered_user["password"]
        assert user.password_hash.startswith("$argon2id$")


def test_duplicate_email_is_rejected(client: TestClient, registered_user: dict[str, str]) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Another Grower",
            "email": registered_user["email"],
            "password": "Greenhouse1",
            "confirm_password": "Greenhouse1",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_registration_validates_password_mismatch(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "Greenhouse1",
            "confirm_password": "Greenhouse2",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_registration_validates_password_strength(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Weak Password",
            "email": "weak@example.com",
            "password": "abc",
            "confirm_password": "abc",
        },
    )
    assert response.status_code == 422


def test_registration_validates_email_format(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Bad Email",
            "email": "not-an-email",
            "password": "Greenhouse1",
            "confirm_password": "Greenhouse1",
        },
    )
    assert response.status_code == 422


def test_login_with_wrong_password_is_rejected(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": "WrongPassword1"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_protected_route_requires_a_session(client: TestClient) -> None:
    response = client.get("/api/analysis")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_session_cookie_is_http_only(client: TestClient, registered_user: dict[str, str]) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
            "remember": True,
        },
    )
    assert response.status_code == 200

    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith("ph_session="))
    csrf_cookie = next(c for c in cookies if c.startswith("ph_csrf="))

    assert "HttpOnly" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "SameSite=lax" in session_cookie.lower().replace("samesite=lax", "SameSite=lax")


def test_logout_revokes_the_session(client: TestClient, registered_user: dict[str, str]) -> None:
    login = client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
            "remember": False,
        },
    )
    assert login.status_code == 200

    headers = csrf_headers(client)
    logout = client.post("/api/auth/logout", headers=headers)
    assert logout.status_code == 200

    me = client.get("/api/auth/me")
    assert me.status_code == 401


def test_state_changing_request_requires_a_csrf_token(
    client: TestClient, registered_user: dict[str, str]
) -> None:
    client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    response = client.post("/api/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_TOKEN_MISSING"


def test_profile_can_be_updated(client: TestClient, registered_user: dict[str, str]) -> None:
    client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    headers = csrf_headers(client)
    response = client.patch("/api/auth/me", json={"full_name": "Renamed Grower"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed Grower"


def test_forgot_password_reports_when_email_delivery_is_unavailable(client: TestClient) -> None:
    response = client.post("/api/auth/forgot-password", json={"email": "someone@example.com"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EMAIL_DELIVERY_NOT_CONFIGURED"
