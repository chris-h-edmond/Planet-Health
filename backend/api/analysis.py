"""Analysis endpoints: prediction, history and individual records."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.deps import (
    enforce_csrf,
    get_app_settings,
    get_current_user,
)
from core.config import Settings
from core.database import get_db
from core.errors import NotFoundError, ValidationError
from core.utils import to_jsonable
from db.models import User
from schemas.analysis import (
    AnalysisDetail,
    AnalysisSummary,
    PaginatedAnalyses,
    PredictionResponse,
)
from services import analysis_service
from services.image_validation import validate_upload
from services.model_service import model_service

logger = logging.getLogger("planethealth.analysis")

router = APIRouter(prefix="/analysis", tags=["Analysis"])

MAX_PAGE_SIZE = 100


@router.post(
    "/predict",
    summary="Analyse a plant image with both models",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": PredictionResponse, "description": "The combined model prediction."},
        422: {"description": "The uploaded file is not a valid image."},
        503: {"description": "The analysis models are unavailable."},
    },
    response_model=None,
)
def predict(
    file: UploadFile = File(..., description="A JPEG or PNG image of a plant leaf."),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    user: User = Depends(get_current_user),
    _: None = Depends(enforce_csrf),
) -> JSONResponse:
    """Run the stress classification and growth estimation models on an image.

    The response body is exactly the output of the existing
    `predict_image()` helper.  The identifier of the stored analysis is
    returned in the `X-Analysis-Id` and `Location` headers so the contract of
    the prediction payload stays untouched.
    """
    data = _read_upload(file, settings)
    validate_upload(data=data, declared_content_type=file.content_type, settings=settings)

    # The models may be unavailable; `predict()` raises a 503 in that case.
    prediction = model_service.predict(data)
    prediction = to_jsonable(prediction)

    record = analysis_service.create_analysis(db, user_id=user.id, prediction=prediction)

    logger.info(
        "Analysis %s created for user %s (label=%s)",
        record.id,
        user.id,
        record.stress_label,
    )

    return JSONResponse(
        content=prediction,
        status_code=status.HTTP_200_OK,
        headers={
            "X-Analysis-Id": str(record.id),
            "Location": f"/api/analysis/{record.id}",
        },
    )


def _read_upload(file: UploadFile, settings: Settings) -> bytes:
    """Read the uploaded payload, enforcing the configured size limit."""
    limit = settings.max_upload_size_bytes

    declared_size = getattr(file, "size", None)
    if declared_size is not None and declared_size > limit:
        raise ValidationError(
            f"The image is larger than the {settings.max_upload_size_mb} MB upload limit."
        )

    try:
        data = file.file.read(limit + 1)
    except Exception as exc:  # noqa: BLE001 - malformed multipart payload
        raise ValidationError("The uploaded file could not be read.") from exc
    finally:
        try:
            file.file.close()
        except Exception:  # pragma: no cover - defensive
            pass

    if len(data) > limit:
        raise ValidationError(
            f"The image is larger than the {settings.max_upload_size_mb} MB upload limit."
        )
    return data


@router.get(
    "",
    response_model=PaginatedAnalyses,
    summary="List the signed-in user's analyses",
)
def list_analyses(
    page: int = Query(1, ge=1, description="1-based page number."),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Rows per page."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaginatedAnalyses:
    records, total = analysis_service.list_analyses(
        db, user_id=user.id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedAnalyses(
        items=[AnalysisSummary.from_record(record) for record in records],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisDetail,
    summary="Fetch a single analysis owned by the signed-in user",
)
def get_analysis(
    analysis_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisDetail:
    record = analysis_service.get_analysis(db, user_id=user.id, analysis_id=analysis_id)
    if record is None:
        # Records belonging to another user are indistinguishable from missing
        # records, which prevents cross-account enumeration.
        raise NotFoundError("That analysis could not be found.", code="ANALYSIS_NOT_FOUND")

    return AnalysisDetail(
        id=record.id,
        created_at=record.created_at,
        stress={
            "label": record.stress_label,
            "stress_score": record.stress_score,
            "score_scale": record.score_scale,
            "probabilities": {
                "healthy": record.healthy_probability,
                "stressed": record.stressed_probability,
            },
        },
        growth={
            "leaf_count": record.leaf_count,
            "leaf_count_rounded": record.leaf_count_rounded,
            "age_days": record.age_days,
        },
    )
