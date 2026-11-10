"""Password reset flow tests."""

from __future__ import annotations

import re

from core.config import get_settings
from fastapi.testclient import TestClient
from services import auth_service, reset_service


def test_forgot_password_reports_when_delivery_is_unavailable(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/forgot-password", json={"email": "someone@example.com"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "EMAIL_DELIVERY_NOT_CONFIGURED"


def test_forgot_password_delivers_a_real_email_when_smtp_is_configured(
    client: TestClient,
    registered_user: dict[str, str],
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "email_delivery_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")

    delivered: dict[str, str] = {}

    def fake_send(_settings, *, to_email, full_name, reset_url):
        delivered["to"] = to_email
        delivered["url"] = reset_url

    monkeypatch.setattr("api.auth.send_password_reset_email", fake_send)

    response = client.post(
        "/api/auth/forgot-password", json={"email": registered_user["email"]}
    )
    assert response.status_code == 200
    assert response.json()["delivery_available"] is True
    assert delivered["to"] == registered_user["email"]
    assert "/reset-password?token=" in delivered["url"]


def test_forgot_password_does_not_reveal_unknown_accounts(
    client: TestClient,
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "email_delivery_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")
    monkeypatch.setattr(
        "api.auth.send_password_reset_email",
        lambda *args, **kwargs: None,
    )

    response = client.post(
        "/api/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert response.status_code == 200
    assert "delivery_available" in response.json()


def test_reset_password_changes_the_password_and_is_single_use(
    client: TestClient,
    registered_user: dict[str, str],
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "email_delivery_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test.local")

    delivered: dict[str, str] = {}

    def fake_send(_settings, *, to_email, full_name, reset_url):
        delivered["url"] = reset_url

    monkeypatch.setattr("api.auth.send_password_reset_email", fake_send)

    client.post(
        "/api/auth/forgot-password", json={"email": registered_user["email"]}
    )

    match = re.search(r"token=([\w\-]+)", delivered["url"])
    assert match is not None
    token = match.group(1)

    reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewGreenhouse2",
            "confirm_new_password": "NewGreenhouse2",
        },
    )
    assert reset.status_code == 200

    # The new password works and the old one does not.
    login = client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": "NewGreenhouse2",
        },
    )
    assert login.status_code == 200

    client.post("/api/auth/logout")
    old = client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert old.status_code == 401

    # The token cannot be replayed.
    replay = client.post(
        "/api/auth/reset-password",
        json={
            "token": token,
            "new_password": "AnotherPass3",
            "confirm_new_password": "AnotherPass3",
        },
    )
    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_reset_password_rejects_an_unknown_token(client: TestClient) -> None:
    response = client.post(
        "/api/auth/reset-password",
        json={
            "token": "totally-made-up-token-value",
            "new_password": "AnotherPass3",
            "confirm_new_password": "AnotherPass3",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_RESET_TOKEN"


def test_reset_token_is_stored_only_as_a_digest(
    client: TestClient,
    registered_user: dict[str, str],
) -> None:
    from core.database import SessionLocal

    with SessionLocal() as db:
        user = auth_service.get_user_by_email(db, registered_user["email"])
        assert user is not None
        raw_token, record = reset_service.create_reset_token(db, user=user)
        assert raw_token not in record.token_hash
        assert record.token_hash != raw_token
