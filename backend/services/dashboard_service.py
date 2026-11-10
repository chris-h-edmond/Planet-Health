"""Dashboard statistics derived from real database records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from schemas.analysis import DashboardStats
from sqlalchemy.orm import Session

from services import analysis_service

RECENT_WINDOW_DAYS = 7


def get_stats(db: Session, *, user_id: int) -> DashboardStats:
    """Compute the dashboard summary for a user.

    Every value is aggregated from the `analyses` table — nothing is
    hardcoded and no user ever sees another user's records.
    """
    counts = analysis_service.stress_label_counts(db, user_id=user_id)
    total = sum(counts.values())

    healthy = counts.get("Healthy", 0)
    stressed = counts.get("Stressed", 0)

    since = datetime.now(UTC) - timedelta(days=RECENT_WINDOW_DAYS)
    recent = analysis_service.count_since(db, user_id=user_id, since=since)

    average_score = analysis_service.average_stress_score(db, user_id=user_id)
    last_at = analysis_service.last_analysis_at(db, user_id=user_id)

    healthy_rate = (healthy / total) if total else 0.0

    return DashboardStats(
        total_analyses=total,
        healthy_count=healthy,
        stressed_count=stressed,
        recent_analyses_count=recent,
        recent_window_days=RECENT_WINDOW_DAYS,
        healthy_rate=round(healthy_rate, 4),
        average_stress_score=round(average_score, 4),
        last_analysis_at=last_at,
    )
