from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from statistics import mean
from typing import Literal

from app.config import settings
from app.deps import ma_watch_store, market_data_provider
from app.ma.email import send_ma_alert_email
from app.ma.state import MAWatchState
from app.market_data.exceptions import MarketDataUnavailable
from app.trading_calendar.tase_calendar import TASE_TZ, tase_close_time_for_date

log = logging.getLogger(__name__)


def _classify(short_ma: float, long_ma: float) -> Literal["golden", "death"] | None:
    if short_ma > long_ma:
        return "golden"
    if short_ma < long_ma:
        return "death"
    return None  # exact tie -- caller holds the previous state


async def ma_poller_loop() -> None:
    """Background task, entirely separate from the pair-spread poller_loop:
    own interval, own schedule (once per trading day, well after close,
    rather than every tick), own failure isolation per watch.
    """
    while True:
        try:
            await asyncio.sleep(settings.ma_poll_interval_seconds)
            await _ma_poll_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("ma poller tick failed unexpectedly")


async def _ma_poll_once() -> None:
    now_local = datetime.now(UTC).astimezone(TASE_TZ)
    today_local = now_local.date()

    close_t = tase_close_time_for_date(today_local)
    if close_t is None:
        return  # not a trading day

    check_after = datetime.combine(today_local, close_t, tzinfo=TASE_TZ) + timedelta(
        minutes=settings.ma_check_delay_minutes
    )
    if now_local < check_after:
        return  # too early today

    for watch in ma_watch_store.list_all():
        if watch.status != "active" or watch.last_checked_date == today_local:
            continue
        try:
            await _check_one_watch(watch, today_local)
        except Exception:
            log.exception("ma check failed for watch %s (%s), continuing with other watches", watch.id, watch.ticker)


async def _check_one_watch(watch: MAWatchState, today_local: date) -> None:
    try:
        history = await asyncio.to_thread(market_data_provider.get_history, watch.ticker, watch.long_period)
    except MarketDataUnavailable as exc:
        await ma_watch_store.apply_check_error(watch.id, str(exc))
        return

    last_close_date = history[-1].as_of.astimezone(TASE_TZ).date()
    if last_close_date != today_local:
        # Yahoo hasn't published today's close yet -- defer, retry later the
        # same day, rather than silently classifying against a stale close.
        await ma_watch_store.apply_check_error(
            watch.id, f"latest close available is {last_close_date}, expected {today_local}"
        )
        return

    closes = [q.price for q in history]
    short_ma = mean(closes[-watch.short_period :])
    long_ma = mean(closes)  # history is already sized to exactly long_period

    current = _classify(short_ma, long_ma)
    is_first_check = watch.last_checked_date is None

    if is_first_check:
        new_direction = current
        should_alert = False
    elif current is None:
        new_direction = watch.last_cross_direction
        should_alert = False
    elif current != watch.last_cross_direction:
        new_direction = current
        should_alert = True
    else:
        new_direction = current
        should_alert = False

    alerted_at: datetime | None = None
    if should_alert:
        # Mutate a copy so send_ma_alert_email sees the new direction in its
        # subject/body without racing the store's own persisted state.
        watch_for_email = watch.model_copy(update={"last_cross_direction": new_direction})
        try:
            await asyncio.to_thread(send_ma_alert_email, watch_for_email, short_ma, long_ma)
            alerted_at = datetime.now(UTC)
            log.info("ma alert sent for watch %s (%s): %s cross", watch.id, watch.ticker, new_direction)
        except Exception:
            # Don't advance last_cross_direction on a failed send -- tomorrow's
            # check will re-fire if the cross is still in effect. Still
            # record today as checked (see apply_check_result's docstring).
            log.exception("ma alert email failed for watch %s, will re-fire if still crossed tomorrow", watch.id)
            new_direction = watch.last_cross_direction

    await ma_watch_store.apply_check_result(
        watch.id,
        checked_date=today_local,
        short_ma=short_ma,
        long_ma=long_ma,
        cross_direction=new_direction,
        alerted=alerted_at is not None,
        alerted_at=alerted_at,
    )
