from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from .config import AppConfig


class EmailConfigurationError(RuntimeError):
    pass


def send_email(
    *,
    config: AppConfig,
    recipient: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
) -> None:
    if not config.smtp_host or not config.smtp_username or not config.smtp_password:
        raise EmailConfigurationError(
            "SMTP credentials are not configured. Set SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((config.smtp_from_name, config.smtp_from_email or config.smtp_username))
    message["To"] = recipient
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(body)

    if config.smtp_use_tls:
        with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(config.smtp_username, config.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port) as smtp:
            smtp.login(config.smtp_username, config.smtp_password)
            smtp.send_message(message)


__all__ = ["send_email", "EmailConfigurationError"]
