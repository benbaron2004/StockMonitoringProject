from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.trading_calendar.holidays import (
    TASE_FULL_CLOSURE_DATES_2026,
    TASE_SHORTENED_SESSIONS_2026,
)

TASE_TZ = ZoneInfo("Asia/Jerusalem")

# Monday=0 .. Sunday=6. TASE trades Mon-Fri since the Jan 5, 2026 calendar change.
TASE_TRADING_WEEKDAYS: set[int] = {0, 1, 2, 3, 4}

TASE_SESSION_WINDOWS: dict[int, tuple[time, time]] = {
    0: (time(9, 59), time(17, 14)),  # Mon
    1: (time(9, 59), time(17, 14)),  # Tue
    2: (time(9, 59), time(17, 14)),  # Wed
    3: (time(9, 59), time(17, 14)),  # Thu
    4: (time(9, 59), time(13, 34)),  # Fri
}


def is_tase_trading_now(now_utc: datetime) -> bool:
    """Whether TASE is currently in a live trading session.

    `now_utc` must be timezone-aware (any timezone); it is converted to
    Israel local time internally, which handles IST/IDT DST transitions via
    the OS tz database rather than manual offset arithmetic.
    """
    local = now_utc.astimezone(TASE_TZ)
    today = local.date()

    if today in TASE_FULL_CLOSURE_DATES_2026:
        return False

    if today in TASE_SHORTENED_SESSIONS_2026:
        open_t, close_t = TASE_SHORTENED_SESSIONS_2026[today]
        return open_t <= local.time() <= close_t

    if local.weekday() not in TASE_TRADING_WEEKDAYS:
        return False

    open_t, close_t = TASE_SESSION_WINDOWS[local.weekday()]
    return open_t <= local.time() <= close_t
