"""Second pass for names resolve_ta125_tickers.py couldn't match -- these are
mostly short/generic names (e.g. "Discount", "Nova", "BIG") whose Yahoo
Finance search results get crowded out by unrelated global tickers. Retries
with fuller company names; still goes through the same TLV+EQUITY filter and
live-price verification, so a wrong guess just fails to resolve rather than
getting included.

Usage:
    python -m scripts.resolve_ta125_retry > /tmp/ta125_retry.json
"""

from __future__ import annotations

import json
import sys
import time

from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider
from scripts.resolve_ta125_tickers import resolve_symbol

# original name -> better search query, based on the companies' full/official
# English names (still verified automatically below, not trusted blindly).
RETRY_QUERIES = {
    "GavYam Lands": "Gav-Yam Lands Corporation",
    "Newmed Energy LP": "NewMed Energy",
    "Meitav Investment House": "Meitav Dash Investments",
    "Discount": "Israel Discount Bank",
    "Elco": "Elco Holdings",
    "Electra": "Electra Ltd holdings",
    "First Intl Bank": "First International Bank of Israel",
    "Harel": "Harel Insurance Investments",
    "Mivne Real Estate KD": "Mivne Real Estate KD Ltd",
    "ICL Israel Chemicals": "ICL Group",
    "Menora Miv Hld": "Menora Mivtachim Holdings",
    "Bazan": "Bazan Group Oil Refineries",
    "Phoenix Holdings": "Phoenix Holdings Insurance",
    "Partner": "Partner Communications",
    "Paz Oil": "Paz Oil Company",
    "Teva": "Teva Pharmaceutical Industries",
    "Tower": "Tower Semiconductor",
    "Delta": "Delta Galil Industries",
    "Formula": "Formula Systems",
    "IES": "I.E.S. Israel Electronics System",
    "Nova": "Nova Ltd measuring instruments",
    "Ratio L": "Ratio Oil Exploration",
    "Sella Real Estate": "Sella Capital Real Estate",
    "Summit": "Summit Real Estate Holdings",
    "BIG": "Big Shopping Centers",
    "FOX": "Fox Wizel",
    "Enlight Energy": "Enlight Renewable Energy",
    "IDI Insurance": "IDI Insurance Company",
    "Shapir Engineering Industry": "Shapir Engineering and Industry",
    "YD More Invest": "More Investment House",
    "Navitas Petroleum Unit": "Navitas Petroleum",
    "Fattal 1998": "Fattal Holdings",
    "FIBI Holdings": "First International Bank Holdings",
    "Doral Energy": "Doral Renewable Energy",
    "OY Nofar Energy": "Nofar Energy",
    "Keystone Reit": "Keystone Real Estate Investment Trust",
    "Econergy Renewable Energy": "Econergy Renewable Energy Ltd",
}


def main() -> None:
    provider = YFinanceProvider()
    resolved: list[dict] = []
    still_unresolved: list[str] = []

    for original_name, query in RETRY_QUERIES.items():
        match = resolve_symbol(query)
        time.sleep(0.3)
        if not match:
            still_unresolved.append(original_name)
            print(f"STILL UNRESOLVED: {original_name!r} (tried {query!r})", file=sys.stderr)
            continue

        try:
            provider.get_price(match["symbol"])
            match["query"] = original_name  # keep the original name for traceability
            resolved.append(match)
            print(f"OK: {original_name!r} -> {match['symbol']} ({match['name']})", file=sys.stderr)
        except MarketDataUnavailable as exc:
            still_unresolved.append(original_name)
            print(f"NO PRICE: {original_name!r} -> {match['symbol']}: {exc}", file=sys.stderr)
        time.sleep(0.3)

    print(json.dumps({"resolved": resolved, "still_unresolved": still_unresolved}, indent=2))
    print(f"\n{len(resolved)} resolved, {len(still_unresolved)} still unresolved", file=sys.stderr)


if __name__ == "__main__":
    main()
