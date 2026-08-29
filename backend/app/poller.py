from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from app.alerts.email import send_alert_email
from app.config import settings
from app.deps import market_data_provider, session_store
from app.market_data.exceptions import MarketDataUnavailable
from app.trading_calendar.tase_calendar import is_tase_trading_now

log = logging.getLogger(__name__)


async def poller_loop() -> None:
    """Background task: one fixed-interval tick per iteration. Sequential by
    construction (sleep -> work -> sleep -> work), so ticks can never overlap.
    """
    while True:
        try:
            await asyncio.sleep(settings.poll_interval_seconds)
            await _poll_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("poller tick failed unexpectedly")


async def _poll_once() -> None:
    state = session_store.snapshot()
    if state.status != "active":
        return
    if not is_tase_trading_now(datetime.now(UTC)):
        return

    try:
        quote_a = await asyncio.to_thread(market_data_provider.get_price, state.ticker_a)
        quote_b = await asyncio.to_thread(market_data_provider.get_price, state.ticker_b)
    except MarketDataUnavailable as exc:
        log.warning("poll tick skipped: %s", exc)
        await session_store.apply_poll_update(last_poll_error=str(exc))
        return

    pct_a = (quote_a.price - state.baseline_price_a) / state.baseline_price_a * 100
    pct_b = (quote_b.price - state.baseline_price_b) / state.baseline_price_b * 100
    spread = abs(pct_a - pct_b)

    alerted: bool | None = None
    alerted_at: datetime | None = None
    if not state.alerted and state.threshold_pct is not None and spread >= state.threshold_pct:
        try:
            await asyncio.to_thread(send_alert_email, state, pct_a, pct_b, spread)
            alerted = True
            alerted_at = datetime.now(UTC)
            log.info("alert sent: %s vs %s spread=%.2f%%", state.ticker_a, state.ticker_b, spread)
        except Exception:
            # Not marked alerted -> retried automatically on the next tick.
            log.exception("alert email failed, will retry next tick")

    await session_store.apply_poll_update(
        price_a=quote_a.price,
        price_b=quote_b.price,
        alerted=alerted,
        alerted_at=alerted_at,
        last_poll_error=None,
    )
