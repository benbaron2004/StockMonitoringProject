from __future__ import annotations

from datetime import datetime
from typing import NamedTuple, Protocol


class PriceQuote(NamedTuple):
    ticker: str
    price: float  # always in ILS (shekels), regardless of what unit the underlying source reports in
    as_of: datetime


class MarketDataProvider(Protocol):
    """Anything that can answer "what's this ticker trading at right now"
    (and, for indicator features, "what has it closed at recently").

    Swapping data sources later (e.g. a real-time paid feed) means writing a
    new class that satisfies this Protocol -- nothing else in the app should
    need to change.
    """

    def get_price(self, ticker: str) -> PriceQuote: ...

    def get_history(self, ticker: str, num_periods: int) -> list[PriceQuote]:
        """The most recent `num_periods` daily closes for `ticker`, oldest
        first, each already in ILS. Raises MarketDataUnavailable if fewer
        than `num_periods` closes are available. Whether the *last* close is
        recent enough for a given caller's purposes is that caller's concern
        (this method has no notion of "today").
        """
        ...
