"""Model lifecycle, availability reporting and inference execution.

This module is the **only** place in the application that knows about the
PyTorch checkpoints.  It deliberately contains no HTTP handling: routes talk
to it through a small, explicit API (`status()` / `predict()`).

Integration contract with the research project
----------------------------------------------
`backend/inference.py` (transferred from the original research repository)
exposes::

    load_models(growth_checkpoint=..., stress_checkpoint=..., device=None) -> PlantModels
    predict_image(image, models_bundle) -> dict

The service below:

* imports that module **without modifying it**;
* calls `load_models(...)` once during application startup;
* stores the returned bundle;
* calls `predict_image(image_bytes, models_bundle)` for every upload.

If the module or the checkpoints are missing, the service reports the correct
availability state and the API answers `503` — it never fabricates a result.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from enum import Enum
from types import ModuleType
from typing import Any

from core.config import BACKEND_ROOT, Settings, get_settings
from core.errors import AppError, ServiceUnavailableError

logger = logging.getLogger("planethealth.models")


class ModelStatus(str, Enum):
    """Lifecycle states of the analysis models."""

    NOT_CONFIGURED = "not_configured"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


#: Stable error codes exposed to clients.
STATUS_CODES: dict[ModelStatus, str] = {
    ModelStatus.NOT_CONFIGURED: "MODEL_NOT_CONFIGURED",
    ModelStatus.LOADING: "MODEL_LOADING",
    ModelStatus.READY: "MODEL_READY",
    ModelStatus.FAILED: "MODEL_LOAD_FAILED",
}

#: Human readable messages used by the API and the UI.
STATUS_MESSAGES: dict[ModelStatus, str] = {
    ModelStatus.NOT_CONFIGURED: "Plant analysis models are not configured.",
    ModelStatus.LOADING: "Plant analysis models are still loading.",
    ModelStatus.READY: "Plant analysis models are ready.",
    ModelStatus.FAILED: "Plant analysis models failed to initialise.",
}


class ModelService:
    """Owns the model bundle, its lifecycle state and inference execution."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._status: ModelStatus = ModelStatus.NOT_CONFIGURED
        self._detail: str | None = None
        self._bundle: Any | None = None
        self._inference: ModuleType | None = None
        self._lock = threading.RLock()
        self._executor: ThreadPoolExecutor | None = None
        self._semaphore: threading.BoundedSemaphore | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def load(self) -> ModelStatus:
        """Load the checkpoints once.  Safe to call more than once."""
        with self._lock:
            if self._status is ModelStatus.READY:
                return self._status

            self._ensure_executor()

            if not self._settings.model_load_on_startup:
                self._set_status(
                    ModelStatus.NOT_CONFIGURED,
                    "Automatic model loading is disabled (MODEL_LOAD_ON_STARTUP=false).",
                )
                return self._status

            try:
                module = self._import_inference()
            except ModuleNotFoundError as exc:
                self._set_status(
                    ModelStatus.NOT_CONFIGURED,
                    f"A runtime dependency required by inference.py is missing ({exc.name}).",
                )
                return self._status

            if module is None:
                self._set_status(
                    ModelStatus.NOT_CONFIGURED,
                    "backend/inference.py has not been transferred into this repository yet.",
                )
                return self._status

            missing = [
                str(path)
                for path in (self._settings.growth_checkpoint, self._settings.stress_checkpoint)
                if not path.is_file()
            ]
            if missing:
                self._set_status(
                    ModelStatus.NOT_CONFIGURED,
                    "Missing checkpoint file(s): " + ", ".join(missing),
                )
                return self._status

            self._set_status(ModelStatus.LOADING, "Loading model checkpoints.")
            self._inference = module

            try:
                bundle = self._call_load_models(module)
            except Exception as exc:  # noqa: BLE001 - surfaced through the status endpoint
                logger.exception("Model initialisation failed")
                self._set_status(
                    ModelStatus.FAILED,
                    f"Model checkpoints could not be loaded ({type(exc).__name__}).",
                )
                return self._status

            self._bundle = bundle
            self._set_status(ModelStatus.READY, "Plant analysis models are ready.")
            return self._status

    def shutdown(self) -> None:
        """Release the inference executor."""
        with self._lock:
            if self._executor is not None:
                self._executor.shutdown(wait=False, cancel_futures=True)
                self._executor = None

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
    @property
    def status(self) -> ModelStatus:
        return self._status

    @property
    def is_ready(self) -> bool:
        return self._status is ModelStatus.READY and self._bundle is not None

    def status_payload(self) -> dict[str, Any]:
        """The body returned by `GET /api/models/status`."""
        code = STATUS_CODES[self._status]
        return {
            "status": self._status.value,
            "code": code,
            "available": self.is_ready,
            "availability": "available" if self.is_ready else "unavailable",
            "message": STATUS_MESSAGES[self._status],
            "detail": self._detail,
            "models": {
                "stress": self._status is ModelStatus.READY,
                "growth": self._status is ModelStatus.READY,
            },
            "device": self._device_label(),
            "checkpoints": {
                "stress": str(self._settings.stress_checkpoint),
                "growth": str(self._settings.growth_checkpoint),
            },
        }

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        """Run both models against ``image_bytes`` and return the raw prediction.

        The prediction is produced by the existing `predict_image()` helper.
        Nothing is generated, defaulted or filled in by this method.
        """
        if not self.is_ready or self._bundle is None:
            raise ServiceUnavailableError(
                STATUS_MESSAGES[self._status],
                code=STATUS_CODES[self._status],
            )

        predict_image = getattr(self._inference, "predict_image", None)
        if predict_image is None:  # pragma: no cover - defensive
            raise ServiceUnavailableError(
                "The inference module does not expose predict_image().",
                code="MODEL_NOT_CONFIGURED",
            )

        executor = self._ensure_executor()
        semaphore = self._semaphore
        assert semaphore is not None  # noqa: S101 - ensured by _ensure_executor

        if not semaphore.acquire(blocking=False):
            # Refuse rather than queue unbounded work — concurrent inference
            # jobs would otherwise be able to exhaust available memory.
            raise ServiceUnavailableError(
                "The analysis service is busy. Please retry in a moment.",
                code="MODEL_BUSY",
            )

        future: Future | None = None
        try:
            # `predict_image(image, models_bundle)` — exactly the contract of
            # the existing research implementation.
            future = executor.submit(predict_image, image_bytes, self._bundle)
            result = future.result(timeout=self._settings.inference_timeout_seconds)
        except FutureTimeoutError:
            if future is not None:
                future.cancel()
            logger.error("Inference exceeded the %ss timeout.", self._settings.inference_timeout_seconds)
            raise AppError(
                status_code=504,
                code="INFERENCE_TIMEOUT",
                message="The analysis took too long to complete. Please try again.",
            ) from None
        except ServiceUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 - any inference failure is reported uniformly
            logger.exception("Prediction execution failed")
            raise AppError(
                status_code=500,
                code="INFERENCE_FAILED",
                message="The plant analysis could not be completed because the model raised an error.",
                details={"reason": type(exc).__name__},
            ) from exc
        finally:
            semaphore.release()

        return self._validate_prediction(result)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _ensure_executor(self) -> ThreadPoolExecutor:
        with self._lock:
            if self._executor is None:
                max_workers = max(1, int(self._settings.inference_max_concurrency))
                self._executor = ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="ph-inference",
                )
            if self._semaphore is None:
                self._semaphore = threading.BoundedSemaphore(
                    max(1, int(self._settings.inference_max_concurrency))
                )
            return self._executor

    def _set_status(self, status: ModelStatus, detail: str | None) -> None:
        self._status = status
        self._detail = detail
        logger.info("Model status changed to %s (%s)", status.value, detail or "-")

    def _import_inference(self) -> ModuleType | None:
        """Import the transferred `inference.py` without altering it."""
        if self._inference is not None:
            return self._inference

        module: ModuleType | None = None
        try:
            import inference  # type: ignore[import-not-found]

            module = inference
        except ModuleNotFoundError as exc:
            if exc.name and exc.name != "inference":
                # A dependency of inference.py (torch, torchvision, PIL) is
                # unavailable — that is a genuine environment failure.
                raise
            candidate = BACKEND_ROOT / "inference.py"
            if candidate.is_file():
                spec = importlib.util.spec_from_file_location("planethealth_inference", candidate)
                if spec is not None and spec.loader is not None:
                    loaded = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(loaded)
                    module = loaded
        except Exception as exc:  # noqa: BLE001 - import-time failure of the module
            logger.exception("Failed to import inference module")
            raise AppError(
                status_code=500,
                code="MODEL_IMPORT_FAILED",
                message="The inference module could not be imported.",
                details={"reason": type(exc).__name__},
            ) from exc

        self._inference = module
        return module

    def _call_load_models(self, module: ModuleType) -> Any:
        """Invoke `load_models()` with the checkpoint paths of this repository.

        The original helper carries default checkpoint paths pointing at the
        research layout.  Rather than editing that working code, the paths are
        supplied here as keyword arguments whenever the signature accepts
        them.
        """
        load_models = getattr(module, "load_models", None)
        if load_models is None:
            raise AttributeError("inference.load_models is not available")

        kwargs: dict[str, Any] = {}
        try:
            parameters = inspect.signature(load_models).parameters
        except (TypeError, ValueError):  # pragma: no cover - builtins without signature
            parameters = {}

        if "growth_checkpoint" in parameters:
            kwargs["growth_checkpoint"] = str(self._settings.growth_checkpoint)
        if "stress_checkpoint" in parameters:
            kwargs["stress_checkpoint"] = str(self._settings.stress_checkpoint)
        if "device" in parameters:
            device = self._resolve_device()
            if device is not None:
                kwargs["device"] = device

        logger.info(
            "Loading models (growth=%s, stress=%s, device=%s)",
            self._settings.growth_checkpoint,
            self._settings.stress_checkpoint,
            kwargs.get("device", "auto"),
        )
        return load_models(**kwargs)

    def _resolve_device(self) -> str | None:
        requested = self._settings.model_device
        if requested == "auto":
            return None
        if requested == "cuda":
            try:
                import torch

                if not torch.cuda.is_available():
                    logger.warning("MODEL_DEVICE=cuda requested but CUDA is unavailable; using CPU.")
                    return "cpu"
            except Exception:  # pragma: no cover - torch not installed yet
                return "cpu"
        return requested

    def _device_label(self) -> str:
        if self._status is not ModelStatus.READY:
            return "unavailable"
        try:

            device = getattr(self._bundle, "device", None)
            if device is not None:
                return str(device)
            return str(next(self._bundle.parameters()).device)  # type: ignore[union-attr]
        except Exception:  # pragma: no cover - defensive
            return self._settings.model_device

    @staticmethod
    def _validate_prediction(result: Any) -> dict[str, Any]:
        """Ensure the helper returned the expected contract.

        Nothing is substituted or repaired — an unexpected shape is an error,
        never a fabricated prediction.
        """
        if not isinstance(result, dict):
            raise AppError(
                status_code=500,
                code="INFERENCE_INVALID_RESULT",
                message="The model returned an unexpected result.",
            )

        stress = result.get("stress")
        growth = result.get("growth")
        if not isinstance(stress, dict) or not isinstance(growth, dict):
            raise AppError(
                status_code=500,
                code="INFERENCE_INVALID_RESULT",
                message="The model returned an unexpected result.",
            )

        required_stress = ("label", "stress_score", "probabilities")
        required_growth = ("leaf_count", "leaf_count_rounded", "age_days")
        for key in required_stress:
            if key not in stress:
                raise AppError(
                    status_code=500,
                    code="INFERENCE_INVALID_RESULT",
                    message="The model returned an unexpected result.",
                )
        for key in required_growth:
            if key not in growth:
                raise AppError(
                    status_code=500,
                    code="INFERENCE_INVALID_RESULT",
                    message="The model returned an unexpected result.",
                )

        probabilities = stress.get("probabilities")
        if not isinstance(probabilities, dict) or "healthy" not in probabilities or "stressed" not in probabilities:
            raise AppError(
                status_code=500,
                code="INFERENCE_INVALID_RESULT",
                message="The model returned an unexpected result.",
            )

        return result


#: Application-wide singleton used by the FastAPI lifespan and the routes.
model_service = ModelService()
