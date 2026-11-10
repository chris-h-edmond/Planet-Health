"""Shared FastAPI dependencies: authentication, CSRF and cookies."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime

from core.config import Settings, get_settings
from core.database import get_db
from core.errors import AppError, AuthenticationError
from core.security import hash_token
from db.models import User, UserSession
from fastapi import Depends, Request, Response
from services import auth_service
from sqlalchemy.orm import Session


@dataclass
class SessionContext:
    """The authenticated session together with its owning user."""

    record: UserSession
    user: User
    raw_token: str


def get_app_settings() -> Settings:
    return get_settings()


def get_client_ip(request: Request) -> str:
    """Best-effort client IP, honouring a single reverse-proxy header."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def get_session_context(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> SessionContext:
    """Resolve the session cookie into an authenticated context."""
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AuthenticationError("You must be signed in to access this resource.")

    record = auth_service.get_session_by_token(db, token)
    if record is None:
        raise AuthenticationError("Your session has expired. Please sign in again.")

    user = auth_service.get_user_by_id(db, record.user_id)
    if user is None:  # pragma: no cover - defensive
        raise AuthenticationError("Your session is no longer valid.")

    return SessionContext(record=record, user=user, raw_token=token)


def get_current_user(context: SessionContext = Depends(get_session_context)) -> User:
    """The authenticated user."""
    return context.user


def enforce_csrf(
    request: Request,
    context: SessionContext = Depends(get_session_context),
    settings: Settings = Depends(get_app_settings),
) -> None:
    """Validate the CSRF token for cookie-authenticated state changes.

    Two independent checks are performed:

    1. the `X-CSRF-Token` header must hash to the token bound to the session
       (double-submit pattern);
    2. when the browser sends an `Origin` header it must match the configured
       allow-list.
    """
    header_token = request.headers.get("x-csrf-token", "")
    if not header_token:
        raise AppError(
            status_code=403,
            code="CSRF_TOKEN_MISSING",
            message="The security token for this request is missing. Please reload the page.",
        )

    if not hmac.compare_digest(hash_token(header_token), context.record.csrf_token_hash):
        raise AppError(
            status_code=403,
            code="CSRF_TOKEN_INVALID",
            message="The security token for this request is invalid. Please reload the page.",
        )

    origin = request.headers.get("origin")
    if origin and settings.allowed_origins:
        allowed = {value.rstrip("/") for value in settings.allowed_origins}
        if origin.rstrip("/") not in allowed:
            raise AppError(
                status_code=403,
                code="ORIGIN_NOT_ALLOWED",
                message="The request origin is not allowed.",
            )


def enforce_trusted_origin(
    request: Request,
    settings: Settings = Depends(get_app_settings),
) -> None:
    """Origin check for unauthenticated state-changing endpoints."""
    origin = request.headers.get("origin")
    if not origin or not settings.allowed_origins:
        return
    allowed = {value.rstrip("/") for value in settings.allowed_origins}
    if origin.rstrip("/") not in allowed:
        raise AppError(
            status_code=403,
            code="ORIGIN_NOT_ALLOWED",
            message="The request origin is not allowed.",
        )


# ----------------------------------------------------------------------
# Cookie helpers
# ----------------------------------------------------------------------
def set_session_cookies(
    response: Response,
    *,
    settings: Settings,
    session_token: str,
    csrf_token: str,
    expires_at: datetime,
    remember: bool,
) -> None:
    """Write the session and CSRF cookies."""
    max_age: int | None = None
    if remember:
        remaining = expires_at - datetime.now(UTC)
        max_age = max(0, int(remaining.total_seconds()))

    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=max_age,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )
    # A readable marker so the browser knows that a session *may* exist and
    # does not have to call the API (and receive a 401) to find out.
    response.set_cookie(
        settings.session_hint_cookie_name,
        "1",
        max_age=max_age,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
    )


def clear_session_cookies(response: Response, *, settings: Settings) -> None:
    """Remove the session, CSRF and hint cookies."""
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path="/",
        domain=settings.cookie_domain,
    )
    response.delete_cookie(
        settings.session_hint_cookie_name,
        path="/",
        domain=settings.cookie_domain,
    )
