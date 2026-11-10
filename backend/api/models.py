"""Model availability endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.model_service import model_service

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "/status",
    summary="Report whether plant analysis inference is available",
)
def get_model_status() -> JSONResponse:
    """Describe the current state of the analysis models.

    The frontend uses this endpoint to decide whether the upload interface
    should be enabled and to explain why an analysis could not be performed.
    """
    payload = model_service.status_payload()
    return JSONResponse(content=payload)
