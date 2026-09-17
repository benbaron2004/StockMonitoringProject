from __future__ import annotations

import logging
import time
from datetime import UTC, date, datetime, timedelta

import yfinance as yf

from app.market_data.base import PriceQuote
from app.market_data.exceptions import MarketDataUnavailable

log = logging.getLogger(__name__)

# Reject a reading that jumps more than this fraction from the last known
# good price in a single poll tick -- cheap protection against a scraping
# glitch (e.g. a stale/garbled value from Yahoo) rather than a real move.
MAX_TICK_JUMP_FRACTION = 0.20

# yfinance is an unofficial, occasionally-flaky scraper -- a single failed
# fetch is often just a transient blip, not a real outage. Retry a couple of
# times with a short delay before giving up.
MAX_FETCH_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 0.75

# Yahoo Finance reports TASE-listed instruments in agorot (1/100 ILS), e.g.
# Teva shows as ~10940 rather than ~109.40. Normalize to ILS here, at the
# data-source boundary, so nothing downstream (poller, session %-change math,
# price display) needs to know or care about the source's raw unit.
AGOROT_PER_ILS = 100

# Calendar-day buffer for a requested number of trading days. Empirically
# measured against real TASE history (not a theoretical 7/5 weekend ratio):
# the actual calendar-to-trading-day ratio for TASE data on Yahoo runs from
# ~1.59 at a 1-year window up to ~1.83 at 15+ years -- notably worse than a
# naive weekends-only estimate, and it doesn't level off at a fixed value
# for the small windows this was originally tuned for. 2.0 + 30 keeps a
# safety margin above the worst observed ratio even at the largest window
# this app ever requests (5Y + a 500-period SMA lookback cap, ~1760 trading
# days -> ~3550 calendar days requested, comfortably covering it).
CALENDAR_DAYS_PER_TRADING_DAY = 2.0
HOLIDAY_PAD_DAYS = 30


class YFinanceProvider:
    """MarketDataProvider backed by yfinance (unofficial Yahoo Finance scraper).

    Free, delayed (~15 min), no API key. This is the only place in the app
    that talks to yfinance -- everything else depends on the MarketDataProvider
    Protocol, so this class can be swapped for a paid/real-time provider later
    without touching the poller, session, or API layers.
    """

    def __init__(self) -> None:
        self._last_good_price: dict[str, float] = {}

    def get_price(self, ticker: str) -> PriceQuote:
        price = self._fetch_price_with_retry(ticker) / AGOROT_PER_ILS
        self._check_outlier(ticker, price)
        self._last_good_price[ticker] = price
        return PriceQuote(ticker=ticker, price=price, as_of=datetime.now(UTC))

    def get_history(self, ticker: str, num_periods: int) -> list[PriceQuote]:
        # Deliberately separate from get_price's retry path (not a shared
        # helper) -- keeps this addition from touching the tested retry
        # behavior of _fetch_price_with_retry.
        rows = self._fetch_history_with_retry(ticker, num_periods)
        return [PriceQuote(ticker=ticker, price=price / AGOROT_PER_ILS, as_of=as_of) for as_of, price in rows]

    def _fetch_history_with_retry(self, ticker: str, num_periods: int) -> list[tuple[datetime, float]]:
        last_error: MarketDataUnavailable | None = None
        for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
            try:
                return self._fetch_history(ticker, num_periods)
            except MarketDataUnavailable as exc:
                last_error = exc
                if attempt < MAX_FETCH_ATTEMPTS:
                    log.warning(
                        "history fetch attempt %d/%d failed for %s, retrying: %s",
                        attempt,
                        MAX_FETCH_ATTEMPTS,
                        ticker,
                        exc,
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
        assert last_error is not None
        raise last_error

    def _fetch_history(self, ticker: str, num_periods: int) -> list[tuple[datetime, float]]:
        days_back = int(num_periods * CALENDAR_DAYS_PER_TRADING_DAY) + HOLIDAY_PAD_DAYS
        end = date.today() + timedelta(days=1)  # yfinance's `end` is exclusive
        start = end - timedelta(days=days_back)

        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start, end=end, interval="1d", auto_adjust=True)
        except Exception as exc:  # noqa: BLE001 - yfinance can raise all sorts
            raise MarketDataUnavailable(ticker, f"history fetch failed: {exc}") from exc

        if hist.empty:
            raise MarketDataUnavailable(ticker, "no historical data returned")

        # Yahoo sometimes inserts a synthetic non-trading row on an ex-dividend
        # date (Volume 0, OHLC all NaN, only the Dividends column populated).
        # It isn't a real close, so drop it before counting/trimming to
        # num_periods -- otherwise a NaN "close" survives the `close <= 0`
        # guard below (NaN comparisons are always False) and poisons every
        # downstream moving average from that date onward.
        hist = hist[hist["Close"].notna()]
        if hist.empty:
            raise MarketDataUnavailable(ticker, "no historical data returned")

        hist = hist.tail(num_periods)
        if len(hist) < num_periods:
            raise MarketDataUnavailable(
                ticker, f"only {len(hist)} of {num_periods} requested daily closes available"
            )

        rows: list[tuple[datetime, float]] = []
        for idx, row in hist.iterrows():
            close = float(row["Close"])
            if close <= 0:
                raise MarketDataUnavailable(ticker, f"non-positive close ({close}) in historical data")
            as_of = idx.to_pydatetime()
            if as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=UTC)
            rows.append((as_of, close))
        return rows

    def _fetch_price_with_retry(self, ticker: str) -> float:
        last_error: MarketDataUnavailable | None = None
        for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
            try:
                return self._fetch_price(ticker)
            except MarketDataUnavailable as exc:
                last_error = exc
                if attempt < MAX_FETCH_ATTEMPTS:
                    log.warning(
                        "price fetch attempt %d/%d failed for %s, retrying: %s",
                        attempt,
                        MAX_FETCH_ATTEMPTS,
                        ticker,
                        exc,
                    )
                    time.sleep(RETRY_DELAY_SECONDS)
        assert last_error is not None
        raise last_error

    def _fetch_price(self, ticker: str) -> float:
        t = yf.Ticker(ticker)

        try:
            fast_info = t.fast_info
            price = fast_info.get("last_price") if hasattr(fast_info, "get") else fast_info.last_price
            if price is not None and price > 0:
                return float(price)
        except Exception as exc:  # noqa: BLE001 - yfinance can raise all sorts
            log.warning("fast_info failed for %s: %s", ticker, exc)

        try:
            hist = t.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if price > 0:
                    return price
        except Exception as exc:  # noqa: BLE001
            log.warning("history fallback failed for %s: %s", ticker, exc)

        raise MarketDataUnavailable(ticker, "no price from fast_info or history fallback")

    def _check_outlier(self, ticker: str, price: float) -> None:
        last = self._last_good_price.get(ticker)
        if last is None:
            return
        jump = abs(price - last) / last
        if jump > MAX_TICK_JUMP_FRACTION:
            raise MarketDataUnavailable(
                ticker,
                f"price jumped {jump:.0%} from last known {last} to {price} in one tick, rejecting as likely glitch",
            )
