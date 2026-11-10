"""Authentication and session management.

Sessions are server-side records.  The browser receives an opaque, random
token in an HTTP-only cookie; only the SHA-256 digest of that token is stored
in PostgreSQL.  A parallel, readable cookie carries the CSRF token which must
be echoed in the `X-CSRF-Token` header for state-changing requests.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import Settings
from core.errors import AuthenticationError, ConflictError
from core.security import generate_token, hash_password, hash_token, verify_password
from db.models import User, UserSession

EMAIL_MAX_LENGTH = 320


def normalise_email(email: str) -> str:
    """Normalise an email address for storage and lookup."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == normalise_email(email))
    return db.execute(stmt).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def email_exists(db: Session, email: str) -> bool:
    return get_user_by_email(db, email) is not None


def create_user(db: Session, *, full_name: str, email: str, password: str) -> User:
    """Create a user with an Argon2id password hash."""
    normalised = normalise_email(email)
    if email_exists(db, normalised):
        raise ConflictError(
            "An account with this email address already exists.",
            code="EMAIL_ALREADY_REGISTERED",
        )

    user = User(
        full_name=full_name.strip(),
        email=normalised,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    """Validate credentials and return the user.

    Raises `AuthenticationError` with a deliberately generic message so that
    the endpoint cannot be used to enumerate accounts.
    """
    user = get_user_by_email(db, email)
    if user is None:
        # Perform a dummy verification so that a missing account and a wrong
        # password take a comparable amount of time.
        verify_password(password, _DUMMY_HASH)
        raise AuthenticationError(
            "Incorrect email or password.", code="INVALID_CREDENTIALS"
        )

    if not verify_password(password, user.password_hash):
        raise AuthenticationError(
            "Incorrect email or password.", code="INVALID_CREDENTIALS"
        )

    return user


#: A valid Argon2id hash of an unusable password, used for timing equalisation.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHRzb21lc2FsdA$"
    "3pQx0y0kH8hWLZU4bhXKx0K8K3lJ0mZq1e1uJ0kQ3g"
)


def session_lifetime(settings: Settings, remember: bool) -> timedelta:
    seconds = (
        settings.session_remember_lifetime_seconds
        if remember
        else settings.session_lifetime_seconds
    )
    return timedelta(seconds=seconds)


def create_session(
    db: Session,
    *,
    user: User,
    settings: Settings,
    remember: bool = False,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[UserSession, str, str, datetime]:
    """Create a session and return it with the raw session and CSRF tokens."""
    now = datetime.now(timezone.utc)
    expires_at = now + session_lifetime(settings, remember)

    session_token = generate_token(32)
    csrf_token = generate_token(32)

    record = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_token(session_token),
        csrf_token_hash=hash_token(csrf_token),
        remember=remember,
        expires_at=expires_at,
        last_seen_at=now,
        created_at=now,
        user_agent=(user_agent or "")[:255] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record, session_token, csrf_token, expires_at


def get_session_by_token(db: Session, token: str) -> UserSession | None:
    """Look up a live session by its raw token."""
    if not token:
        return None

    stmt = select(UserSession).where(UserSession.token_hash == hash_token(token))
    record = db.execute(stmt).scalar_one_or_none()
    if record is None:
        return None

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(record)
        db.commit()
        return None

    return record


def refresh_session(db: Session, record: UserSession, settings: Settings) -> datetime:
    """Extend the sliding expiry of a session and return the new expiry."""
    now = datetime.now(timezone.utc)
    lifetime = session_lifetime(settings, record.remember)
    record.expires_at = now + lifetime
    record.last_seen_at = now
    db.commit()
    db.refresh(record)
    return record.expires_at


def should_refresh(record: UserSession, settings: Settings) -> bool:
    """Return True when the sliding refresh window has elapsed."""
    last_seen = record.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last_seen).total_seconds()
    return elapsed >= settings.session_refresh_interval_seconds


def revoke_session(db: Session, record: UserSession) -> None:
    db.delete(record)
    db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> None:
    stmt = select(UserSession).where(UserSession.user_id == user_id)
    for record in db.execute(stmt).scalars().all():
        db.delete(record)
    db.commit()


def purge_expired_sessions(db: Session) -> int:
    """Delete expired session rows.  Returns the number of removed rows."""
    now = datetime.now(timezone.utc)
    stmt = select(UserSession).where(UserSession.expires_at <= now)
    removed = 0
    for record in db.execute(stmt).scalars().all():
        db.delete(record)
        removed += 1
    if removed:
        db.commit()
    return removed


def update_password(db: Session, *, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    db.commit()


def update_profile(db: Session, *, user: User, full_name: str) -> User:
    user.full_name = full_name.strip()
    db.commit()
    db.refresh(user)
    return user
