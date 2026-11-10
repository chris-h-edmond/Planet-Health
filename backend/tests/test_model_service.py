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


def test_models_are_loaded_with_the_repository_checkpoint_paths(
    tmp_path, monkeypatch
) -> None:
    """The Phase 2 wiring: load_models() receives this repository's paths."""
    import types

    from core.config import get_settings

    calls: dict[str, object] = {}

    module = types.ModuleType("inference")

    class PlantModels:
        def __init__(self) -> None:
            self.device = "cpu"

    def load_models(growth_checkpoint=None, stress_checkpoint=None, device=None):
        calls["load"] = (growth_checkpoint, stress_checkpoint, device)
        return PlantModels()

    def predict_image(image, models_bundle):
        calls["predict"] = (image, models_bundle)
        return {
            "stress": {
                "label": "Healthy",
                "stress_score": 0.13,
                "score_scale": "0-1",
                "probabilities": {"healthy": 0.87, "stressed": 0.13},
            },
            "growth": {
                "leaf_count": 8.4,
                "leaf_count_rounded": 8,
                "age_days": 26.2,
            },
        }

    module.load_models = load_models
    module.predict_image = predict_image

    growth = tmp_path / "growth_model.pth"
    stress = tmp_path / "stress_model.pth"
    growth.write_bytes(b"checkpoint")
    stress.write_bytes(b"checkpoint")

    settings = get_settings().model_copy()
    settings.model_load_on_startup = True
    settings.model_growth_checkpoint = growth
    settings.model_stress_checkpoint = stress

    service = ModelService(settings)
    monkeypatch.setattr(service, "_import_inference", lambda: module)

    assert service.load() is ModelStatus.READY
    assert service.is_ready is True

    # The checkpoint paths of this repository are passed explicitly, so the
    # defaults inside the transferred inference.py are never used.
    assert calls["load"] == (str(growth), str(stress), None)

    result = service.predict(b"image-bytes")
    assert result["stress"]["label"] == "Healthy"
    assert result["growth"]["leaf_count_rounded"] == 8

    # predict_image(image, models_bundle) — exactly the research contract.
    assert calls["predict"][0] == b"image-bytes"
    assert isinstance(calls["predict"][1], PlantModels)

    payload = service.status_payload()
    assert payload["available"] is True
    assert payload["status"] == "ready"
    assert payload["code"] == "MODEL_READY"


def test_a_ready_prediction_is_persisted_with_the_contract_values(
    tmp_path, monkeypatch
) -> None:
    """The values returned by the models are what reaches PostgreSQL."""
    import types

    from core.config import get_settings
    from core.database import SessionLocal
    from services import analysis_service, auth_service

    module = types.ModuleType("inference")
    module.load_models = lambda **kwargs: types.SimpleNamespace(device="cpu")
    module.predict_image = lambda image, bundle: {
        "stress": {
            "label": "Stressed",
            "stress_score": 0.87,
            "score_scale": "0-1",
            "probabilities": {"healthy": 0.13, "stressed": 0.87},
        },
        "growth": {"leaf_count": 8.4, "leaf_count_rounded": 8, "age_days": 26.2},
    }

    growth = tmp_path / "growth_model.pth"
    stress = tmp_path / "stress_model.pth"
    growth.write_bytes(b"checkpoint")
    stress.write_bytes(b"checkpoint")

    settings = get_settings().model_copy()
    settings.model_load_on_startup = True
    settings.model_growth_checkpoint = growth
    settings.model_stress_checkpoint = stress

    service = ModelService(settings)
    monkeypatch.setattr(service, "_import_inference", lambda: module)
    assert service.load() is ModelStatus.READY

    prediction = service.predict(b"image-bytes")

    with SessionLocal() as db:
        user = auth_service.create_user(
            db,
            full_name="Phase Two",
            email="phase2@example.com",
            password="Greenhouse1",
        )
        record = analysis_service.create_analysis(
            db, user_id=user.id, prediction=prediction
        )

        assert record.stress_label == "Stressed"
        assert record.stress_score == 0.87
        assert record.score_scale == "0-1"
        assert record.healthy_probability == 0.13
        assert record.stressed_probability == 0.87
        assert record.leaf_count == 8.4
        assert record.leaf_count_rounded == 8
        assert record.age_days == 26.2
        assert record.created_at is not None
