"""Upload validation.

Uploaded images are validated before they ever reach the models:

1. the declared content type must be an accepted image type;
2. the payload must not exceed the configured size limit;
3. the bytes must actually decode as a JPEG or PNG image;
4. the decoded image must not exceed the pixel budget.

Filenames and content types supplied by the client are never trusted on their
own — the image is decoded and inspected.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from core.config import Settings
from core.errors import ValidationError
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger("planethealth.uploads")

#: Pillow format identifiers that are accepted.
ACCEPTED_FORMATS: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
}

#: Formats that Pillow can decode but that are not accepted (e.g. GIF, BMP).
_REJECTED_FORMAT_HINTS = {
    "GIF": "GIF images are not supported.",
    "BMP": "BMP images are not supported.",
    "TIFF": "TIFF images are not supported.",
    "WEBP": "WEBP images are not supported.",
    "PDF": "PDF files are not supported.",
}


@dataclass(frozen=True)
class ValidatedImage:
    """Metadata about a successfully validated upload."""

    content_type: str
    format: str
    width: int
    height: int
    size_bytes: int


def validate_upload(
    *,
    data: bytes,
    declared_content_type: str | None,
    settings: Settings,
) -> ValidatedImage:
    """Validate an uploaded image payload.

    Raises `ValidationError` (HTTP 422) with a user-facing message when the
    upload is not an acceptable image.
    """
    if not data:
        raise ValidationError("The uploaded file is empty.")

    if len(data) > settings.max_upload_size_bytes:
        raise ValidationError(
            f"The image is larger than the {settings.max_upload_size_mb} MB upload limit."
        )

    normalised_type = (declared_content_type or "").split(";")[0].strip().lower()
    if normalised_type and normalised_type not in settings.allowed_image_mime_types:
        raise ValidationError(
            "Unsupported file type. Please upload a JPEG or PNG image.",
            {"allowed": settings.allowed_image_mime_types},
        )

    try:
        with Image.open(io.BytesIO(data)) as probe:
            image_format = (probe.format or "").upper()
            width, height = probe.size
    except UnidentifiedImageError as exc:
        raise ValidationError(
            "The uploaded file could not be read as an image. Please upload a JPEG or PNG file."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - Pillow raises many decode errors
        logger.info("Rejected upload: %s", exc)
        raise ValidationError(
            "The uploaded file could not be read as an image. Please upload a JPEG or PNG file."
        ) from exc

    if image_format in _REJECTED_FORMAT_HINTS:
        raise ValidationError(_REJECTED_FORMAT_HINTS[image_format])

    if image_format not in ACCEPTED_FORMATS:
        raise ValidationError(
            "Unsupported image format. Please upload a JPEG or PNG image.",
            {"detected_format": image_format or "unknown"},
        )

    detected_type = ACCEPTED_FORMATS[image_format]
    if normalised_type and normalised_type != detected_type:
        raise ValidationError(
            "The file content does not match the declared file type.",
            {"declared": normalised_type, "detected": detected_type},
        )

    if width * height > settings.max_image_pixels:
        raise ValidationError(
            "The image resolution is too large to be processed.",
            {"max_pixels": settings.max_image_pixels},
        )

    # `verify()` re-checks the integrity of the file without decoding pixels.
    try:
        with Image.open(io.BytesIO(data)) as verified:
            verified.verify()
    except Exception as exc:  # noqa: BLE001 - corrupt payload
        logger.info("Rejected corrupt upload: %s", exc)
        raise ValidationError("The uploaded image appears to be corrupted.") from exc

    return ValidatedImage(
        content_type=detected_type,
        format=image_format,
        width=width,
        height=height,
        size_bytes=len(data),
    )
