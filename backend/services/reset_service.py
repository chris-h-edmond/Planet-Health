"""Password reset tokens.

The reset link contains a raw token; only its SHA-256 digest is stored.
Tokens are single use and expire after a short window.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from core.security import generate_token, hash_token
from db.models import PasswordResetToken, User
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from services.auth_service import get_user_by_id

#: How long a reset link stays valid.
RESET_TOKEN_LIFETIME = timedelta(minutes=60)


def create_reset_token(
    db: Session,
    *,
    user: User,
) -> tuple[str, PasswordResetToken]:
    """Create a reset token for a user and return the raw token and record."""
    now = datetime.now(UTC)

    # Any previously issued token for this account is invalidated.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = generate_token(32)
    record = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=now + RESET_TOKEN_LIFETIME,
        created_at=now,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return raw_token, record


def consume_reset_token(db: Session, *, raw_token: str) -> User | None:
    """Validate a reset token and return the owning user.

    The token is marked as used so that it cannot be replayed.
    """
    if not raw_token:
        return None

    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hash_token(raw_token)
    )
    record = db.execute(stmt).scalar_one_or_none()
    if record is None or record.used_at is not None:
        return None

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        return None

    record.used_at = datetime.now(UTC)
    db.commit()

    return get_user_by_id(db, record.user_id)


def purge_expired_tokens(db: Session) -> int:
    """Delete tokens that are used or expired. Returns the number removed."""
    now = datetime.now(UTC)
    stmt = select(PasswordResetToken).where(
        (PasswordResetToken.expires_at <= now) | (PasswordResetToken.used_at.is_not(None))
    )
    removed = 0
    for record in db.execute(stmt).scalars().all():
        db.delete(record)
        removed += 1
    if removed:
        db.commit()
    return removed
