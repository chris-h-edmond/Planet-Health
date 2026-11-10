"""Request and response schemas for analysis, history and dashboard endpoints.

The `stress` and `growth` objects mirror the output of the existing
`inference.predict_image()` helper exactly.  They are the authoritative
contract between the ML layer, the database layer and the frontend.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StressProbabilities(BaseModel):
    healthy: float = Field(..., ge=0.0, le=1.0)
    stressed: float = Field(..., ge=0.0, le=1.0)


class StressPrediction(BaseModel):
    """Output of the plant stress classification model."""

    label: str = Field(..., examples=["Stressed"])
    stress_score: float = Field(..., ge=0.0, le=1.0)
    score_scale: str = Field(default="0-1")
    probabilities: StressProbabilities


class GrowthPrediction(BaseModel):
    """Output of the plant growth estimation model."""

    leaf_count: float = Field(..., ge=0.0)
    leaf_count_rounded: int = Field(..., ge=0)
    age_days: float = Field(..., ge=0.0)


class PredictionResponse(BaseModel):
    """The successful prediction payload — identical to `predict_image()` output."""

    stress: StressPrediction
    growth: GrowthPrediction


class AnalysisSummary(BaseModel):
    """A single row of the analysis history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stress_label: str
    stress_score: float
    healthy_probability: float
    stressed_probability: float
    leaf_count: float
    leaf_count_rounded: int
    age_days: float
    created_at: datetime

    @classmethod
    def from_record(cls, record) -> AnalysisSummary:
        return cls(
            id=record.id,
            stress_label=record.stress_label,
            stress_score=record.stress_score,
            healthy_probability=record.healthy_probability,
            stressed_probability=record.stressed_probability,
            leaf_count=record.leaf_count,
            leaf_count_rounded=record.leaf_count_rounded,
            age_days=record.age_days,
            created_at=record.created_at,
        )


class AnalysisDetail(BaseModel):
    """Full analysis record including the prediction payload."""

    id: uuid.UUID
    created_at: datetime
    stress: StressPrediction
    growth: GrowthPrediction


class PaginatedAnalyses(BaseModel):
    items: list[AnalysisSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    """Aggregated statistics — always derived from real database records."""

    total_analyses: int
    healthy_count: int
    stressed_count: int
    recent_analyses_count: int
    recent_window_days: int
    healthy_rate: float
    average_stress_score: float
    last_analysis_at: datetime | None
