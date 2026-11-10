"""Dashboard statistics endpoint."""

from __future__ import annotations

from core.database import get_db
from db.models import User
from fastapi import APIRouter, Depends
from schemas.analysis import DashboardStats
from services import dashboard_service
from sqlalchemy.orm import Session

from api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Aggregated statistics for the signed-in user",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DashboardStats:
    """Return dashboard statistics calculated from the user's own records."""
    return dashboard_service.get_stats(db, user_id=user.id)
