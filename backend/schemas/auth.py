"""Request and response schemas for the authentication endpoints."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 256

PASSWORD_REQUIREMENTS = (
    "At least 8 characters, including an uppercase letter, a lowercase letter and a number."
)


def _validate_password_strength(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(PASSWORD_REQUIREMENTS)
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password is too long.")
    if not re.search(r"[a-z]", password):
        raise ValueError(PASSWORD_REQUIREMENTS)
    if not re.search(r"[A-Z]", password):
        raise ValueError(PASSWORD_REQUIREMENTS)
    if not re.search(r"\d", password):
        raise ValueError(PASSWORD_REQUIREMENTS)
    return password


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    confirm_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name must contain at least two characters.")
        return cleaned

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def _check_strength(cls, value: str) -> str:
        return _validate_password_strength(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> RegisterRequest:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=MAX_PASSWORD_LENGTH)
    remember: bool = False

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)

    @field_validator("full_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Full name must contain at least two characters.")
        return cleaned


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    confirm_new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("new_password")
    @classmethod
    def _check_strength(cls, value: str) -> str:
        return _validate_password_strength(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> ChangePasswordRequest:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        if self.new_password == self.current_password:
            raise ValueError("The new password must be different from the current password.")
        return self


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=256)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)
    confirm_new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)

    @field_validator("new_password")
    @classmethod
    def _check_strength(cls, value: str) -> str:
        return _validate_password_strength(value)

    @model_validator(mode="after")
    def _passwords_match(self) -> ResetPasswordRequest:
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match.")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    """Returned by register / login / refresh.

    The session itself travels in an HTTP-only cookie; this payload only
    describes the authenticated user.
    """

    user: UserResponse
    expires_at: datetime
