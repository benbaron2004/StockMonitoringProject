"""Manual check: does get_history() return sane data for real TASE tickers?

Usage:
    python -m scripts.check_ma_history TEVA.TA ICL.TA
"""

from __future__ import annotations

import sys
from statistics import mean

from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider


def main(tickers: list[str]) -> None:
    provider = YFinanceProvider()
    for ticker in tickers:
        try:
            hist = provider.get_history(ticker, 200)
            closes = [q.price for q in hist]
            sma50 = mean(closes[-50:])
            sma200 = mean(closes)
            relationship = "golden" if sma50 > sma200 else "death" if sma50 < sma200 else "tie"
            print(
                f"{ticker:10s} rows={len(hist)} "
                f"range={hist[0].as_of.date()}..{hist[-1].as_of.date()} "
                f"last_close={closes[-1]:.2f} sma50={sma50:.2f} sma200={sma200:.2f} ({relationship})"
            )
        except MarketDataUnavailable as exc:
            print(f"{ticker:10s} UNAVAILABLE: {exc.reason}")


if __name__ == "__main__":
    tickers = sys.argv[1:] or ["TEVA.TA", "ICL.TA", "NICE.TA"]
    main(tickers)
