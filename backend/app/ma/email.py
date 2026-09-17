from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import settings
from app.ma.state import MAWatchState


def send_ma_alert_email(watch: MAWatchState, short_ma: float, long_ma: float) -> None:
    cross_word = "Golden" if watch.last_cross_direction == "golden" else "Death"
    msg = EmailMessage()
    msg["Subject"] = f"{watch.ticker}: {cross_word} cross ({watch.short_period}/{watch.long_period}-day SMA)"
    msg["From"] = settings.alert_from_email
    msg["To"] = settings.alert_to_email
    msg.set_content(
        f"{watch.ticker} just had a {cross_word.lower()} cross.\n\n"
        f"{watch.short_period}-day SMA: {short_ma:.2f}\n"
        f"{watch.long_period}-day SMA: {long_ma:.2f}\n\n"
        f"Watch started: {watch.created_at}\n"
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
