from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings
from app.session import SessionState


def send_alert_email(state: SessionState, pct_a: float, pct_b: float, spread: float) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"TASE spread alert: {state.ticker_a} vs {state.ticker_b} crossed {state.threshold_pct}%"
    msg["From"] = settings.alert_from_email
    msg["To"] = settings.alert_to_email
    msg.set_content(
        f"Spread threshold crossed.\n\n"
        f"{state.ticker_a}: {pct_a:+.2f}%\n"
        f"{state.ticker_b}: {pct_b:+.2f}%\n"
        f"Spread: {spread:.2f} percentage points (threshold: {state.threshold_pct}%)\n\n"
        f"Session started: {state.started_at}\n"
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
