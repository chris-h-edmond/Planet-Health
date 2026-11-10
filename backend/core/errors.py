"""Stable application error envelope.

Every error returned by the API uses a single shape so the frontend can rely
on it:

```json
{
  "error": {
    "code": "MODEL_NOT_CONFIGURED",
    "message": "Plant analysis models are not configured.",
    "details": { }
  }
}
```
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("planethealth.errors")


class AppError(Exception):
    """Base class for errors that map onto the stable error envelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details

    def to_payload(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            error["details"] = self.details
        return {"error": error}


class ValidationError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(status_code=422, code="VALIDATION_ERROR", message=message, details=details)


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication required.", code: str = "UNAUTHENTICATED") -> None:
        super().__init__(status_code=401, code=code, message=message)


class PermissionError_(AppError):
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(status_code=403, code="FORBIDDEN", message=message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.", code: str = "NOT_FOUND") -> None:
        super().__init__(status_code=404, code=code, message=message)


class ConflictError(AppError):
    def __init__(self, message: str, code: str = "CONFLICT") -> None:
        super().__init__(status_code=409, code=code, message=message)


class ServiceUnavailableError(AppError):
    def __init__(self, message: str, code: str = "SERVICE_UNAVAILABLE") -> None:
        super().__init__(status_code=503, code=code, message=message)


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many attempts. Please try again later.", retry_after: int = 60) -> None:
        super().__init__(
            status_code=429,
            code="RATE_LIMITED",
            message=message,
            details={"retry_after_seconds": retry_after},
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers that guarantee the stable error envelope."""

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())[1:]) or "body",
                "message": error.get("msg", "Invalid value."),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request payload is invalid.",
                    "details": details,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            413: "PAYLOAD_TOO_LARGE",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internal details or stack traces to the client.
        logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again.",
                }
            },
        )
