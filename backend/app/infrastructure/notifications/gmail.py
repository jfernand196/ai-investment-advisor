"""Gmail SMTP email sender."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

from app.core.config import Settings


@dataclass
class EmailSendResult:
    sent: bool
    provider_message_id: Optional[str]
    error: Optional[str] = None
    skipped: bool = False


class GmailEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        placeholders = {
            "",
            "change-me",
            "your-gmail-app-password",
            "your.email@gmail.com",
        }
        username = (self.settings.smtp_username or "").strip()
        password = (self.settings.smtp_password or "").strip()
        recipient = (self.settings.email_to or username).strip()
        if username in placeholders or password in placeholders or recipient in placeholders:
            return False
        return bool(username and password and recipient)

    def send(self, subject: str, body_text: str, body_html: Optional[str] = None) -> EmailSendResult:
        if not self.configured:
            return EmailSendResult(
                sent=False,
                provider_message_id=None,
                error="SMTP credentials missing (SMTP_USERNAME / SMTP_PASSWORD / EMAIL_TO)",
                skipped=True,
            )

        msg = EmailMessage()
        sender = self.settings.email_from or self.settings.smtp_username
        recipient = self.settings.email_to or self.settings.smtp_username
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(msg)
            return EmailSendResult(sent=True, provider_message_id=None)
        except Exception as exc:  # noqa: BLE001
            return EmailSendResult(sent=False, provider_message_id=None, error=str(exc))
