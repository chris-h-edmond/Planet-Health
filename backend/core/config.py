"""Application configuration.

All runtime configuration is environment-driven.  A `.env` file living next to
the backend package root is loaded automatically for local development.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# `backend/` — the package root that contains `main.py`, `inference.py` and the
# `models/` checkpoint directory.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS_DIR = BACKEND_ROOT / "models"

_INSECURE_DEFAULT_SECRET = "planet-health-insecure-development-secret-key"


def _resolve_checkpoint_path(value: str | Path) -> Path:
    """Resolve a checkpoint path.

    A relative path is always interpreted relative to the backend package
    root, never relative to the current working directory.  This keeps the
    configuration identical for the Docker image, the local development
    server and the test-suite.
    """
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (BACKEND_ROOT / path).resolve()


class Settings(BaseSettings):
    """Central settings object for the Planet Health backend."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = "Planet Health API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://planethealth:planethealth@localhost:5432/planethealth",
        description="SQLAlchemy 2 URL for the application database.",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # ------------------------------------------------------------------
    # Security / sessions
    # ------------------------------------------------------------------
    secret_key: str = Field(
        default=_INSECURE_DEFAULT_SECRET,
        description="Deployment secret. Required to be changed outside development.",
    )
    session_cookie_name: str = "ph_session"
    csrf_cookie_name: str = "ph_csrf"
    session_hint_cookie_name: str = Field(
        default="ph_session_hint",
        description=(
            "A readable marker cookie that tells the browser a session may "
            "exist. It carries no authority — the session cookie remains the "
            "only credential — and it avoids an unnecessary 401 round trip "
            "for anonymous visitors."
        ),
    )
    session_lifetime_seconds: int = Field(
        default=43_200,
        description="Server-side session lifetime for a non-remembered session (12 hours).",
    )
    session_remember_lifetime_seconds: int = Field(
        default=2_592_000,
        description="Server-side session lifetime when 'remember me' is used (30 days).",
    )
    session_refresh_interval_seconds: int = Field(
        default=900,
        description="Sliding refresh window — a session is extended once it has been idle for this long.",
    )
    cookie_secure: bool = Field(
        default=False,
        description="Set to true when the application is served over HTTPS.",
    )
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None

    # ------------------------------------------------------------------
    # CORS / origin allow-list
    # ------------------------------------------------------------------
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Origins allowed to call the API directly from a browser.",
    )
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description="Trusted origins used for the Origin / Referer CSRF check.",
    )

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    login_rate_limit_attempts: int = 8
    login_rate_limit_window_seconds: int = 300
    register_rate_limit_attempts: int = 5
    register_rate_limit_window_seconds: int = 3600

    # ------------------------------------------------------------------
    # Uploads
    # ------------------------------------------------------------------
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    allowed_image_mime_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["image/jpeg", "image/png"],
        description="Content types accepted by the analysis endpoint.",
    )
    max_image_pixels: int = Field(
        default=40_000_000,
        description="Decompression-bomb guard for decoded images.",
    )

    # ------------------------------------------------------------------
    # ML models
    # ------------------------------------------------------------------
    model_growth_checkpoint: Path = DEFAULT_MODELS_DIR / "growth" / "growth_model.pth"
    model_stress_checkpoint: Path = DEFAULT_MODELS_DIR / "stress" / "stress_model.pth"
    model_load_on_startup: bool = True
    model_device: Literal["auto", "cpu", "cuda"] = "auto"
    inference_max_concurrency: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Maximum number of simultaneous PyTorch inference jobs.",
    )
    inference_timeout_seconds: int = Field(
        default=120,
        ge=5,
        description="Maximum wall-clock duration of a single inference job.",
    )

    # ------------------------------------------------------------------
    # Email delivery (password reset)
    # ------------------------------------------------------------------
    email_delivery_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "no-reply@planethealth.local"
    smtp_use_tls: bool = True
    public_app_url: str = "http://localhost:3000"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("secret_key")
    @classmethod
    def _reject_default_secret_in_production(cls, value: str, info) -> str:
        app_env = (info.data or {}).get("app_env", "development")
        if app_env == "production" and value == _INSECURE_DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY must be set to a unique value when APP_ENV=production."
            )
        return value

    @field_validator("cors_allow_origins", "allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_image_mime_types", mode="before")
    @classmethod
    def _split_csv_mime(cls, value):
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return value

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def growth_checkpoint(self) -> Path:
        return _resolve_checkpoint_path(self.model_growth_checkpoint)

    @property
    def stress_checkpoint(self) -> Path:
        return _resolve_checkpoint_path(self.model_stress_checkpoint)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()
