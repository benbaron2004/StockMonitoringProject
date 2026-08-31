from __future__ import annotations

from datetime import datetime
from typing import NamedTuple, Protocol


class PriceQuote(NamedTuple):
    ticker: str
    price: float  # always in ILS (shekels), regardless of what unit the underlying source reports in
    as_of: datetime


class MarketDataProvider(Protocol):
    """Anything that can answer "what's this ticker trading at right now".

    Swapping data sources later (e.g. a real-time paid feed) means writing a
    new class that satisfies this Protocol -- nothing else in the app should
    need to change.
    """

    def get_price(self, ticker: str) -> PriceQuote: ...
