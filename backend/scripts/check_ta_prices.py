"""Manual check: does yfinance return a usable price for these TASE tickers?

Usage:
    python -m scripts.check_ta_prices TEVA.TA ICL.TA NICE.TA
"""

from __future__ import annotations

import sys

from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider


def main(tickers: list[str]) -> None:
    provider = YFinanceProvider()
    for ticker in tickers:
        try:
            quote = provider.get_price(ticker)
            print(f"{ticker:12s} price={quote.price:>12.2f}  as_of={quote.as_of.isoformat()}")
        except MarketDataUnavailable as exc:
            print(f"{ticker:12s} UNAVAILABLE: {exc.reason}")


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["TEVA.TA", "ICL.TA", "NICE.TA", "ESLT.TA", "POLI.TA", "LUMI.TA"]
    main(tickers)
