from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

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
