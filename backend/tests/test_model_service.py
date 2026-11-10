"""Model lifecycle and prediction-contract tests."""

from __future__ import annotations

import pytest

from core.errors import AppError, ServiceUnavailableError
from services.model_service import ModelService, ModelStatus


def test_service_starts_as_not_configured() -> None:
    service = ModelService()
    assert service.status is ModelStatus.NOT_CONFIGURED
    assert service.is_ready is False


def test_status_payload_reports_availability() -> None:
    service = ModelService()
    service.load()

    payload = service.status_payload()
    assert payload["status"] == "not_configured"
    assert payload["code"] == "MODEL_NOT_CONFIGURED"
    assert payload["available"] is False
    assert payload["availability"] == "unavailable"
    assert payload["models"] == {"stress": False, "growth": False}
    assert "message" in payload


def test_predict_raises_service_unavailable_when_not_ready() -> None:
    service = ModelService()
    service.load()

    with pytest.raises(ServiceUnavailableError) as excinfo:
        service.predict(b"not-an-image")

    assert excinfo.value.status_code == 503
    assert excinfo.value.code == "MODEL_NOT_CONFIGURED"


def test_missing_inference_module_is_reported_as_not_configured() -> None:
    from core.config import get_settings

    settings = get_settings().model_copy()
    settings.model_load_on_startup = True

    service = ModelService(settings)
    status = service.load()
    assert status is ModelStatus.NOT_CONFIGURED
    assert "inference.py" in (service.status_payload()["detail"] or "")


def test_missing_checkpoint_is_reported_as_not_configured(tmp_path, monkeypatch) -> None:
    import types

    from core.config import get_settings

    settings = get_settings().model_copy()
    settings.model_load_on_startup = True
    settings.model_growth_checkpoint = tmp_path / "missing.pth"
    settings.model_stress_checkpoint = tmp_path / "missing.pth"

    service = ModelService(settings)
    # Pretend the research inference module has been transferred.
    monkeypatch.setattr(
        service, "_import_inference", lambda: types.ModuleType("inference")
    )

    status = service.load()
    assert status is ModelStatus.NOT_CONFIGURED
    assert "Missing checkpoint" in (service.status_payload()["detail"] or "")


def test_prediction_validation_rejects_an_unexpected_shape() -> None:
    with pytest.raises(AppError) as excinfo:
        ModelService._validate_prediction({"stress": {"label": "Healthy"}})
    assert excinfo.value.code == "INFERENCE_INVALID_RESULT"

    with pytest.raises(AppError) as excinfo:
        ModelService._validate_prediction("not a dict")
    assert excinfo.value.code == "INFERENCE_INVALID_RESULT"


def test_prediction_validation_accepts_the_documented_contract() -> None:
    payload = {
        "stress": {
            "label": "Stressed",
            "stress_score": 0.87,
            "score_scale": "0-1",
            "probabilities": {"healthy": 0.13, "stressed": 0.87},
        },
        "growth": {"leaf_count": 8.4, "leaf_count_rounded": 8, "age_days": 26.2},
    }
    assert ModelService._validate_prediction(payload) == payload
