"""Manual end-to-end check of the real alert email path (uses real SMTP creds
from .env -- run this once you've filled in .env, before deploying).

Sends one alert email directly, bypassing the poller/threshold logic (which
is already covered by the automated FakeMarketDataProvider tests).

Usage:
    python -m scripts.force_alert_test
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.alerts.email import send_alert_email
from app.session import SessionState


def main() -> None:
    state = SessionState(
        status="active",
        ticker_a="TEVA.TA",
        ticker_b="ICL.TA",
        baseline_price_a=100.0,
        baseline_price_b=100.0,
        threshold_pct=2.0,
        started_at=datetime.now(UTC),
    )
    send_alert_email(state, pct_a=3.1, pct_b=0.4, spread=2.7)
    print("Alert email sent -- check the inbox configured as ALERT_TO_EMAIL.")


if __name__ == "__main__":
    main()
