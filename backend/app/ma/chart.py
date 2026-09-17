"""Historical price + moving-average chart data for MA watches.

Deliberately independent of poller.py's crossover-detection logic: this
module computes a full ROLLING array of SMA values for display, whereas
poller.py only ever needs the single latest SMA value for alerting. Neither
module imports the other -- keep it that way.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from typing import Literal, NamedTuple

from app.market_data.base import PriceQuote
from app.trading_calendar.tase_calendar import TASE_TZ

ChartRange = Literal["1W", "1M", "3M", "6M", "1Y", "5Y"]

RANGE_TRADING_DAYS: dict[ChartRange, int] = {
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "1Y": 252,
    "5Y": 1260,
}


class ChartPoint(NamedTuple):
    as_of: date
    close: float
    short_ma: float
    long_ma: float


def fetch_periods_needed(chart_range: ChartRange, short_period: int, long_period: int) -> int:
    """How many trailing daily closes to request from get_history() so every
    displayed point has full lookback for both SMAs, not just the ones after
    enough history accumulates within the visible window itself.
    """
    return RANGE_TRADING_DAYS[chart_range] + max(short_period, long_period)


def trailing_sma(values: Sequence[float], window: int) -> list[float | None]:
    """One output per input value: None until index >= window-1 (not enough
    lookback yet), else the mean of the trailing `window` values. O(n) via a
    running sum, not O(n*window).
    """
    if window <= 0:
        raise ValueError("window must be > 0")
    out: list[float | None] = []
    running = 0.0
    for i, v in enumerate(values):
        running += v
        if i >= window:
            running -= values[i - window]
        out.append(running / window if i >= window - 1 else None)
    return out


def build_chart_points(
    history: list[PriceQuote], *, display_days: int, short_period: int, long_period: int
) -> list[ChartPoint]:
    """Compute rolling SMAs over the full fetched history, then slice to just
    the last `display_days` points. Because the caller always requests
    display_days + max(short_period, long_period) periods (see
    fetch_periods_needed), every sliced point is guaranteed to fall past both
    SMAs' None-prefix -- short_ma/long_ma are never None in the result.
    """
    closes = [q.price for q in history]
    short_series = trailing_sma(closes, short_period)
    long_series = trailing_sma(closes, long_period)

    # Slice BEFORE asserting -- only the last display_days entries are
    # guaranteed to fall past both SMAs' None-prefix. The discarded lookback
    # prefix legitimately contains Nones; asserting before slicing would trip
    # on those every time.
    sliced = list(zip(history, closes, short_series, long_series, strict=True))[-display_days:]

    points: list[ChartPoint] = []
    for quote, close, short_ma, long_ma in sliced:
        # math.isfinite (not just `is not None`) -- a NaN close price from
        # get_history() would poison trailing_sma()'s running sum without
        # ever being None, and NaN would otherwise silently slip past this
        # guard and reach the API response as a schema-violating null.
        assert (
            short_ma is not None and math.isfinite(short_ma) and long_ma is not None and math.isfinite(long_ma)
        ), "caller under-requested lookback or upstream data contained a non-finite price"
        points.append(
            ChartPoint(
                as_of=quote.as_of.astimezone(TASE_TZ).date(),
                close=close,
                short_ma=short_ma,
                long_ma=long_ma,
            )
        )
    return points
