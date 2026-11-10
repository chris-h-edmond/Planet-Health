"""SQLAlchemy ORM models.

The schema deliberately stores **only** prediction values and timestamps for an
analysis.  Uploaded images are processed in memory and discarded; no image
binary is ever written to the database.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from db.base import Base


def utcnow() -> datetime:
    """Timezone-aware current UTC timestamp."""
    return datetime.now(UTC)


class User(Base):
    """A Planet Health account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="noload"
    )
    analyses: Mapped[list[Analysis]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="noload"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User id={self.id} email={self.email!r}>"


class UserSession(Base):
    """A server-side session.

    Only the SHA-256 digest of the session token is stored, so the database
    never contains a usable session credential.
    """

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    remember: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions", lazy="noload")


class PasswordResetToken(Base):
    """A single-use password reset token.

    Only the SHA-256 digest of the token is stored, exactly like the session
    token, so a database leak does not expose usable reset links.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(lazy="noload")


class Analysis(Base):
    """A single plant analysis produced by the stress + growth models."""
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stress_label: Mapped[str] = mapped_column(String(16), nullable=False)
    stress_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_scale: Mapped[str] = mapped_column(String(8), nullable=False, default="0-1")
    healthy_probability: Mapped[float] = mapped_column(Float, nullable=False)
    stressed_probability: Mapped[float] = mapped_column(Float, nullable=False)
    leaf_count: Mapped[float] = mapped_column(Float, nullable=False)
    leaf_count_rounded: Mapped[int] = mapped_column(Integer, nullable=False)
    age_days: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="analyses", lazy="noload")

    __table_args__ = (
        Index("ix_analyses_user_created_at", "user_id", "created_at"),
        Index("ix_analyses_user_stress_label", "user_id", "stress_label"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Analysis id={self.id} user_id={self.user_id} label={self.stress_label!r}>"
