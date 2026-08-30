"""One-off data-gathering helper: resolve TA-125 constituent company names
(from investing.com's components listing, which has no ticker symbols) to
actual Yahoo Finance tickers, then verify each returns a real price.

This is not part of the running app -- it's how config.py's TICKER_PRESETS
list was built/refreshed. Re-run it if the TA-125 composition changes.

Usage:
    python -m scripts.resolve_ta125_tickers > /tmp/ta125_resolved.json
"""

from __future__ import annotations

import json
import sys
import time

import yfinance as yf

from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider

# Company names as listed on investing.com's TA-125 components page
# (fetched 2026-08-30). No ticker symbols given there -- that's what this
# script resolves.
TA125_COMPANY_NAMES = [
    "Afi Prop.", "Alony Hetz", "Amot Investments", "Airport City", "Azorim Investment",
    "Bezeq", "Blue Square", "GavYam Lands", "Cellcom", "Clal Insurance",
    "Newmed Energy LP", "Delek Group", "Meitav Investment House", "Discount", "Elco",
    "Electra Real Estate", "Electra", "Elbit Systems", "First Intl Bank", "Gilat",
    "Harel", "Mivne Real Estate KD", "ICL Israel Chemicals", "Israel Corp", "Isramco Negev",
    "Leumi", "Migdal Insurance", "Melisron", "Menora Miv Hld", "Matrix",
    "Mizrahi Tefahot", "NICE Ltd", "Bazan", "Phoenix Holdings", "Bank Hapoalim",
    "Partner", "Paz Oil", "Rami Levi", "Shufersal", "Shikun & Binui",
    "Strauss Group", "Teva", "Tower", "Aura Investments", "Camtek",
    "Danel", "Delta", "Dimri", "Danya Cebus", "El Al",
    "Equital", "Formula", "Hilan", "IBI Inv House", "IES",
    "Lapidoth", "Nova", "Israel Canada", "Ratio L", "Reit 1",
    "Scope", "Sella Real Estate", "Summit", "Azrieli Group", "Ayalon Insurance",
    "BIG", "Bet Shemesh Engines", "FOX", "Isrotel -L", "Isras",
    "Aryt Industries", "Mega Or", "Mivtach Shamir", "One Software", "Prashkovsky",
    "Propert & Buil", "Qualitau", "Lahav", "Villar", "Neto Malinda",
    "Priortech", "Africa Israel Residences", "Carasso Motors", "Opko Health", "Enlight Energy",
    "IDI Insurance", "Ashtrom Group Ltd", "Energix", "Inrom Construction Industries", "Kenon Holdings",
    "Shapir Engineering Industry", "Ormat", "YD More Invest", "Tamar Petroleum", "OPC Energy",
    "Navitas Petroleum Unit", "Fattal 1998", "Energean", "Isracard", "Generation Capital",
    "TASE", "FIBI Holdings", "Yochananof", "Doral Energy", "Meshek Energy-Renewable Energies",
    "Israel Shipyards", "Max Stock", "OY Nofar Energy", "Wesure Global Tech", "Delta Israel Brands",
    "Nayax", "Argo Properties NV", "Turpaz Industries", "Ackerstein", "Veridis Environment",
    "Keystone Reit", "Next Vision", "Econergy Renewable Energy", "Rimon Consulting Management Services", "Kvutzat Acro",
    "Shikun Binui Energy", "Amram Avraham Construction", "RP Optical Lab", "Ampa Ltd", "Universal Motors Israel",
]


def resolve_symbol(name: str) -> dict | None:
    try:
        results = yf.Search(name, max_results=8).quotes
    except Exception as exc:  # noqa: BLE001
        print(f"  search failed for {name!r}: {exc}", file=sys.stderr)
        return None

    for q in results:
        if q.get("exchange") == "TLV" and q.get("quoteType") == "EQUITY":
            return {"query": name, "symbol": q["symbol"], "name": q.get("longname") or q.get("shortname") or name}
    return None


def main() -> None:
    provider = YFinanceProvider()
    resolved: list[dict] = []
    unresolved: list[str] = []
    price_failed: list[dict] = []

    for name in TA125_COMPANY_NAMES:
        match = resolve_symbol(name)
        time.sleep(0.3)  # be polite to yfinance's search endpoint
        if not match:
            unresolved.append(name)
            print(f"UNRESOLVED: {name}", file=sys.stderr)
            continue

        try:
            provider.get_price(match["symbol"])
            resolved.append(match)
            print(f"OK: {name!r} -> {match['symbol']} ({match['name']})", file=sys.stderr)
        except MarketDataUnavailable as exc:
            price_failed.append({**match, "error": str(exc)})
            print(f"NO PRICE: {name!r} -> {match['symbol']}: {exc}", file=sys.stderr)
        time.sleep(0.3)

    print(
        json.dumps(
            {"resolved": resolved, "unresolved": unresolved, "price_failed": price_failed},
            indent=2,
        )
    )
    print(
        f"\n{len(resolved)} resolved, {len(unresolved)} unresolved, {len(price_failed)} found but no price",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
