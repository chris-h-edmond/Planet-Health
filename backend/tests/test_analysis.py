"""Model status, health and analysis endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import csrf_headers, make_image_bytes


def test_health_endpoint_reports_availability(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["database"] == "ok"
    assert "models" in body


def test_model_status_endpoint(client: TestClient) -> None:
    response = client.get("/api/models/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"not_configured", "loading", "ready", "failed"}
    assert body["available"] is False
    assert body["code"] == "MODEL_NOT_CONFIGURED"
    assert body["availability"] == "unavailable"


def test_prediction_returns_503_when_models_are_unavailable(
    auth_client: TestClient,
) -> None:
    headers = csrf_headers(auth_client)
    response = auth_client.post(
        "/api/analysis/predict",
        files={"file": ("leaf.jpg", make_image_bytes(), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "MODEL_NOT_CONFIGURED"
    assert body["error"]["message"] == "Plant analysis models are not configured."
    # No fabricated prediction may be returned.
    assert "stress" not in body
    assert "growth" not in body


def test_prediction_rejects_a_non_image_upload(auth_client: TestClient) -> None:
    headers = csrf_headers(auth_client)
    response = auth_client.post(
        "/api/analysis/predict",
        files={"file": ("notes.txt", b"this is not an image", "text/plain")},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_prediction_rejects_an_unsupported_image_format(auth_client: TestClient) -> None:
    headers = csrf_headers(auth_client)
    response = auth_client.post(
        "/api/analysis/predict",
        files={"file": ("leaf.bmp", make_image_bytes(fmt="BMP"), "image/bmp")},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_prediction_accepts_an_image_whose_declared_type_differs_from_its_content(
    auth_client: TestClient,
) -> None:
    """A ".png" file that actually contains JPEG data is a real-world case.

    The decoded content is the authority, so the upload must pass validation
    and reach the model check (which reports 503 while the models are absent).
    """
    headers = csrf_headers(auth_client)
    response = auth_client.post(
        "/api/analysis/predict",
        files={"file": ("leaf.png", make_image_bytes(fmt="JPEG"), "image/png")},
        headers=headers,
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "MODEL_NOT_CONFIGURED"


def test_prediction_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/analysis/predict",
        files={"file": ("leaf.jpg", make_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 401


def test_dashboard_stats_start_at_zero(auth_client: TestClient) -> None:
    response = auth_client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_analyses"] == 0
    assert body["healthy_count"] == 0
    assert body["stressed_count"] == 0
    assert body["healthy_rate"] == 0.0


def test_history_is_empty_for_a_new_account(auth_client: TestClient) -> None:
    response = auth_client.get("/api/analysis")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_history_is_scoped_to_the_owning_user(
    client: TestClient, auth_client: TestClient, registered_user: dict[str, str]
) -> None:
    """A second account must not see the analyses of the first one."""
    from core.database import SessionLocal
    from db.models import Analysis
    from services import auth_service

    with SessionLocal() as db:
        owner = auth_service.get_user_by_email(db, registered_user["email"])
        assert owner is not None
        record = Analysis(
            user_id=owner.id,
            stress_label="Healthy",
            stress_score=0.12,
            score_scale="0-1",
            healthy_probability=0.88,
            stressed_probability=0.12,
            leaf_count=8.4,
            leaf_count_rounded=8,
            age_days=26.2,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        analysis_id = str(record.id)

    response = auth_client.get("/api/analysis")
    assert response.status_code == 200
    assert response.json()["total"] == 1

    detail = auth_client.get(f"/api/analysis/{analysis_id}")
    assert detail.status_code == 200
    assert detail.json()["stress"]["label"] == "Healthy"

    # A different account must neither see the record nor its details.
    other = client.post(
        "/api/auth/register",
        json={
            "full_name": "Other Grower",
            "email": "other-grower@example.com",
            "password": "Greenhouse1",
            "confirm_password": "Greenhouse1",
        },
    )
    assert other.status_code == 201

    other_list = client.get("/api/analysis")
    assert other_list.status_code == 200
    assert other_list.json()["total"] == 0

    other_detail = client.get(f"/api/analysis/{analysis_id}")
    assert other_detail.status_code == 404
    assert other_detail.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_dashboard_stats_are_derived_from_records(
    auth_client: TestClient, registered_user: dict[str, str]
) -> None:
    from core.database import SessionLocal
    from db.models import Analysis
    from services import auth_service

    with SessionLocal() as db:
        owner = auth_service.get_user_by_email(db, registered_user["email"])
        assert owner is not None
        for label, score in (("Healthy", 0.1), ("Stressed", 0.9), ("Healthy", 0.2)):
            db.add(
                Analysis(
                    user_id=owner.id,
                    stress_label=label,
                    stress_score=score,
                    score_scale="0-1",
                    healthy_probability=1 - score,
                    stressed_probability=score,
                    leaf_count=5.0,
                    leaf_count_rounded=5,
                    age_days=20.0,
                )
            )
        db.commit()

    response = auth_client.get("/api/dashboard/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_analyses"] == 3
    assert body["healthy_count"] == 2
    assert body["stressed_count"] == 1
    assert body["healthy_rate"] == pytest_approx(2 / 3)


def pytest_approx(value: float, tolerance: float = 0.01):
    import pytest

    return pytest.approx(value, abs=tolerance)
