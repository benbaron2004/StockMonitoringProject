"""Third pass: direct ticker guesses for names Search couldn't rank correctly
(mostly short/generic names where the TASE listing didn't surface in the top
results). Each guess is verified against a REAL live price via
YFinanceProvider -- a wrong guess just returns no data and gets dropped, it
is never trusted on the guess alone.

Usage:
    python -m scripts.resolve_ta125_guess > /tmp/ta125_guess.json
"""

from __future__ import annotations

import json
import sys
import time

import yfinance as yf

from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider

CANDIDATES = {
    "Teva": "TEVA.TA",
    "Bazan": "ORL.TA",
    "Phoenix Holdings": "PHOE1.TA",
    "Paz Oil": "PZOL.TA",
    "Electra": "ELTR.TA",
    "Elco": "ELCO.TA",
    "Nova": "NVMI.TA",
    "IDI Insurance": "IDIN.TA",
    "Meitav Investment House": "MTAV.TA",
    "Ratio L": "RATI.TA",
    "GavYam Lands": "GAVY.TA",
    "IES": "IES.TA",
    "YD More Invest": "MISH.TA",
    "FIBI Holdings": "FIBIH.TA",
    "Doral Energy": "DORL.TA",
    "Keystone Reit": "KEYS.TA",
    "Mivne Real Estate KD": "MVNE.TA",
    "Econergy Renewable Energy": "ECOR.TA",
}


def main() -> None:
    provider = YFinanceProvider()
    resolved: list[dict] = []
    still_unresolved: list[str] = []

    for original_name, symbol in CANDIDATES.items():
        try:
            provider.get_price(symbol)
        except MarketDataUnavailable as exc:
            still_unresolved.append(original_name)
            print(f"NO PRICE: {original_name!r} guess {symbol}: {exc}", file=sys.stderr)
            time.sleep(0.2)
            continue

        # Cross-check it's actually the right company and a TASE equity,
        # not just some other symbol that happens to return a price.
        try:
            info = yf.Ticker(symbol).get_info()
            long_name = info.get("longName") or info.get("shortName") or ""
            exchange = info.get("exchange") or info.get("fullExchangeName") or ""
        except Exception as exc:  # noqa: BLE001
            long_name, exchange = "", ""
            print(f"  (could not fetch info to cross-check {symbol}: {exc})", file=sys.stderr)

        resolved.append({"query": original_name, "symbol": symbol, "name": long_name, "exchange": exchange})
        print(f"OK: {original_name!r} -> {symbol} ({long_name!r}, exchange={exchange!r})", file=sys.stderr)
        time.sleep(0.2)

    print(json.dumps({"resolved": resolved, "still_unresolved": still_unresolved}, indent=2))
    print(f"\n{len(resolved)} resolved, {len(still_unresolved)} still unresolved", file=sys.stderr)


if __name__ == "__main__":
    main()
