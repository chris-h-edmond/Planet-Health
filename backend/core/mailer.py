"""Outbound email delivery.

Password reset is only advertised as available when a real SMTP transport is
configured.  When it is not, the API reports the feature as unavailable
instead of pretending an email was sent.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from core.config import Settings

logger = logging.getLogger("planethealth.mailer")


class EmailDeliveryNotConfigured(RuntimeError):
    """Raised when an email is requested but no SMTP transport is configured."""


def is_available(settings: Settings) -> bool:
    """Return True when a usable SMTP transport has been configured."""
    return bool(settings.email_delivery_enabled and settings.smtp_host)


def send_email(
    settings: Settings,
    *,
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """Send a plain-text email.  Raises `EmailDeliveryNotConfigured` when unset."""
    if not is_available(settings):
        raise EmailDeliveryNotConfigured(
            "SMTP delivery is not configured for this deployment."
        )

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:  # pragma: no cover - depends on live SMTP server
        logger.error("Failed to deliver email to %s: %s", to_email, exc)
        raise


def send_password_reset_email(
    settings: Settings,
    *,
    to_email: str,
    full_name: str,
    reset_url: str,
) -> None:
    """Deliver a password reset link."""
    subject = "Reset your Planet Health password"
    body = (
        f"Hello {full_name},\n\n"
        "Someone requested a password reset for your Planet Health account.\n\n"
        f"Open the link below to choose a new password:\n\n{reset_url}\n\n"
        "The link is valid for 60 minutes and can only be used once.\n"
        "If you did not request this, you can safely ignore this email — "
        "your password has not changed.\n\n"
        "— Planet Health\n"
    )
    send_email(settings, to_email=to_email, subject=subject, body=body)
