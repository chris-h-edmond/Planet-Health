"""Shared response envelopes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["MODEL_NOT_CONFIGURED"])
    message: str = Field(..., examples=["Plant analysis models are not configured."])
    details: Any | None = None


class ErrorResponse(BaseModel):
    """The single error envelope used by every endpoint."""

    error: ErrorDetail


class MessageResponse(BaseModel):
    message: str
