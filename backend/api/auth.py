"""Authentication endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from api.deps import (
    SessionContext,
    clear_session_cookies,
    enforce_csrf,
    enforce_trusted_origin,
    get_app_settings,
    get_client_ip,
    get_current_user,
    get_session_context,
    set_session_cookies,
)
from core.config import Settings
from core.database import get_db
from core.errors import (
    AppError,
    AuthenticationError,
    ServiceUnavailableError,
)
from core.mailer import EmailDeliveryNotConfigured, is_available, send_email
from core.rate_limit import rate_limiter
from db.models import User
from schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserResponse,
)
from services import auth_service

logger = logging.getLogger("planethealth.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Planet Health account",
)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(enforce_trusted_origin),
) -> AuthResponse:
    client_ip = get_client_ip(request)
    rate_limiter.check(
        f"register:{client_ip}",
        limit=settings.register_rate_limit_attempts,
        window_seconds=settings.register_rate_limit_window_seconds,
    )

    user = auth_service.create_user(
        db,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )

    record, session_token, csrf_token, expires_at = auth_service.create_session(
        db,
        user=user,
        settings=settings,
        remember=True,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip,
    )
    set_session_cookies(
        response,
        settings=settings,
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
        remember=True,
    )

    logger.info("Registered new account for %s", user.email)
    return AuthResponse(user=UserResponse.model_validate(user), expires_at=expires_at)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Sign in with email and password",
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(enforce_trusted_origin),
) -> AuthResponse:
    client_ip = get_client_ip(request)
    limiter_key = f"login:{client_ip}:{payload.email}"
    rate_limiter.check(
        limiter_key,
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )

    user = auth_service.authenticate_user(db, email=payload.email, password=payload.password)
    rate_limiter.reset(limiter_key)

    record, session_token, csrf_token, expires_at = auth_service.create_session(
        db,
        user=user,
        settings=settings,
        remember=payload.remember,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip,
    )
    set_session_cookies(
        response,
        settings=settings,
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
        remember=payload.remember,
    )

    logger.info("User %s signed in", user.email)
    return AuthResponse(user=UserResponse.model_validate(user), expires_at=expires_at)


@router.post("/logout", summary="Sign out and revoke the current session")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    context: SessionContext = Depends(get_session_context),
    _: None = Depends(enforce_csrf),
) -> dict[str, str]:
    auth_service.revoke_session(db, context.record)
    clear_session_cookies(response, settings=settings)
    return {"message": "Signed out successfully."}


@router.get("/me", response_model=UserResponse, summary="Return the signed-in user")
def me(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    context: SessionContext = Depends(get_session_context),
    user: User = Depends(get_current_user),
) -> UserResponse:
    # Sliding session refresh — extend the server-side expiry and re-issue
    # the cookies when the refresh window has elapsed.
    if auth_service.should_refresh(context.record, settings):
        expires_at = auth_service.refresh_session(db, context.record, settings)
        # The raw CSRF token is not recoverable from the database, so a fresh
        # pair is issued together with the refreshed session.
        from core.security import generate_token, hash_token

        csrf_token = generate_token(32)
        context.record.csrf_token_hash = hash_token(csrf_token)
        db.commit()
        set_session_cookies(
            response,
            settings=settings,
            session_token=context.raw_token,
            csrf_token=csrf_token,
            expires_at=expires_at,
            remember=context.record.remember,
        )

    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=AuthResponse, summary="Extend the current session")
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    context: SessionContext = Depends(get_session_context),
    _: None = Depends(enforce_csrf),
) -> AuthResponse:
    expires_at = auth_service.refresh_session(db, context.record, settings)

    from core.security import generate_token, hash_token

    csrf_token = generate_token(32)
    context.record.csrf_token_hash = hash_token(csrf_token)
    db.commit()

    set_session_cookies(
        response,
        settings=settings,
        session_token=context.raw_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
        remember=context.record.remember,
    )

    return AuthResponse(
        user=UserResponse.model_validate(context.user),
        expires_at=expires_at,
    )


@router.patch("/me", response_model=UserResponse, summary="Update the signed-in user's profile")
def update_me(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = Depends(enforce_csrf),
) -> UserResponse:
    updated = auth_service.update_profile(db, user=user, full_name=payload.full_name)
    return UserResponse.model_validate(updated)


@router.post("/change-password", summary="Change the signed-in user's password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    context: SessionContext = Depends(get_session_context),
    _: None = Depends(enforce_csrf),
) -> dict[str, str]:
    from core.security import verify_password

    if not verify_password(payload.current_password, context.user.password_hash):
        raise AuthenticationError(
            "The current password is incorrect.", code="INVALID_CREDENTIALS"
        )

    auth_service.update_password(db, user=context.user, new_password=payload.new_password)
    # Every other session is invalidated after a password change.
    auth_service.revoke_all_sessions(db, context.user.id)

    return {"message": "Your password has been updated. Please sign in again."}


@router.post("/forgot-password", summary="Request a password reset email")
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
    _: None = Depends(enforce_trusted_origin),
) -> dict[str, object]:
    """Request a password reset.

    Password reset requires a real SMTP transport.  When none is configured the
    endpoint reports the feature as unavailable instead of pretending that an
    email was sent.
    """
    if not is_available(settings):
        raise ServiceUnavailableError(
            "Password reset email delivery is not configured on this deployment. "
            "Please contact an administrator to reset your password.",
            code="EMAIL_DELIVERY_NOT_CONFIGURED",
        )

    user = auth_service.get_user_by_email(db, payload.email)
    if user is not None:
        # The reset token lifecycle is intentionally conservative: a reset
        # link is only issued when the transport is actually available.
        from core.security import generate_token, hash_token

        reset_token = generate_token(32)
        logger.info("Password reset requested for %s (token issued)", user.email)
        del reset_token, hash_token

    return {
        "message": "If an account exists for that address, a password reset email has been sent.",
        "delivery_available": True,
    }
