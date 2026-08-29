from __future__ import annotations

import logging
from datetime import UTC, datetime

import yfinance as yf

from app.market_data.base import PriceQuote
from app.market_data.exceptions import MarketDataUnavailable

log = logging.getLogger(__name__)

# Reject a reading that jumps more than this fraction from the last known
# good price in a single poll tick -- cheap protection against a scraping
# glitch (e.g. a stale/garbled value from Yahoo) rather than a real move.
MAX_TICK_JUMP_FRACTION = 0.20


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
        price = self._fetch_price(ticker)
        self._check_outlier(ticker, price)
        self._last_good_price[ticker] = price
        return PriceQuote(ticker=ticker, price=price, as_of=datetime.now(UTC))

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
