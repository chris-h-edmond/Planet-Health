"""Analysis persistence.

The prediction values produced by the models are stored; the uploaded image
is never persisted.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import Analysis


def create_analysis(db: Session, *, user_id: int, prediction: dict[str, Any]) -> Analysis:
    """Persist the values of a successful prediction."""
    stress = prediction["stress"]
    growth = prediction["growth"]
    probabilities = stress["probabilities"]

    record = Analysis(
        id=uuid.uuid4(),
        user_id=user_id,
        stress_label=str(stress["label"]),
        stress_score=float(stress["stress_score"]),
        score_scale=str(stress.get("score_scale", "0-1")),
        healthy_probability=float(probabilities["healthy"]),
        stressed_probability=float(probabilities["stressed"]),
        leaf_count=float(growth["leaf_count"]),
        leaf_count_rounded=int(growth["leaf_count_rounded"]),
        age_days=float(growth["age_days"]),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_analyses(
    db: Session,
    *,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Analysis], int]:
    """Return one page of the user's analyses plus the total record count."""
    offset = max(0, (page - 1) * page_size)

    total_stmt = select(func.count()).select_from(Analysis).where(Analysis.user_id == user_id)
    total = int(db.execute(total_stmt).scalar_one())

    stmt = (
        select(Analysis)
        .where(Analysis.user_id == user_id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(page_size)
        .offset(offset)
    )
    items = list(db.execute(stmt).scalars().all())
    return items, total


def get_analysis(db: Session, *, user_id: int, analysis_id: uuid.UUID) -> Analysis | None:
    """Fetch a single analysis, scoped to the owning user.

    Returning `None` for records owned by somebody else prevents cross-account
    enumeration.
    """
    stmt = select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def recent_analyses(db: Session, *, user_id: int, limit: int = 5) -> list[Analysis]:
    stmt = (
        select(Analysis)
        .where(Analysis.user_id == user_id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def count_since(db: Session, *, user_id: int, since: datetime) -> int:
    stmt = (
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.user_id == user_id, Analysis.created_at >= since)
    )
    return int(db.execute(stmt).scalar_one())


def stress_label_counts(db: Session, *, user_id: int) -> dict[str, int]:
    stmt = (
        select(Analysis.stress_label, func.count())
        .where(Analysis.user_id == user_id)
        .group_by(Analysis.stress_label)
    )
    return {label: int(count) for label, count in db.execute(stmt).all()}


def average_stress_score(db: Session, *, user_id: int) -> float:
    stmt = select(func.avg(Analysis.stress_score)).where(Analysis.user_id == user_id)
    value = db.execute(stmt).scalar()
    return float(value) if value is not None else 0.0


def last_analysis_at(db: Session, *, user_id: int) -> datetime | None:
    stmt = select(func.max(Analysis.created_at)).where(Analysis.user_id == user_id)
    return db.execute(stmt).scalar()
