"""Shared pytest fixtures.

The environment is configured **before** the application modules are imported
so that the SQLAlchemy engine is created against a throwaway SQLite database
instead of PostgreSQL.
"""

from __future__ import annotations

import os
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = TEST_DIR.parent

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(BACKEND_ROOT / '.pytest_tmp' / 'test.db').as_posix()}")
os.environ.setdefault("SECRET_KEY", "planet-health-pytest-secret-key-value")
os.environ.setdefault("MODEL_LOAD_ON_STARTUP", "false")
os.environ.setdefault("LOGIN_RATE_LIMIT_ATTEMPTS", "100")
os.environ.setdefault("REGISTER_RATE_LIMIT_ATTEMPTS", "100")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://testserver")
os.environ.setdefault("ALLOWED_ORIGINS", "http://testserver")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from core.database import engine  # noqa: E402
from db import models  # noqa: E402,F401  (registers the ORM mappings)
from db.base import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> None:
    db_path = BACKEND_ROOT / ".pytest_tmp"
    db_path.mkdir(parents=True, exist_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    from main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def registered_user(client: TestClient) -> dict[str, str]:
    """Register a fresh account and return its credentials."""
    payload = {
        "full_name": "Test Grower",
        "email": f"grower-{os.urandom(4).hex()}@example.com",
        "password": "Greenhouse1",
        "confirm_password": "Greenhouse1",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload


@pytest.fixture()
def auth_client(client: TestClient, registered_user: dict[str, str]) -> TestClient:
    """A client that is signed in and able to send CSRF headers."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
            "remember": False,
        },
    )
    assert response.status_code == 200, response.text
    return client


def csrf_headers(client: TestClient) -> dict[str, str]:
    """Build the CSRF header for the client's current session cookie."""
    token = client.cookies.get("ph_csrf")
    return {"X-CSRF-Token": token} if token else {}


def make_image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (64, 64)) -> bytes:
    """Create a small in-memory test image."""
    import io

    buffer = io.BytesIO()
    image = Image.new("RGB", size, color=(34, 120, 60))
    image.save(buffer, format=fmt)
    return buffer.getvalue()
