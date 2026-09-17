"""Process-wide singletons, shared by the API handlers and the poller loop.

Deliberately plain module-level instances rather than FastAPI Depends/DI --
this is a single-process, single-user app with exactly one of each.
"""

from __future__ import annotations

from app.ma.state import MAWatchStore
from app.market_data.yfinance_provider import YFinanceProvider
from app.session import SessionStore

market_data_provider = YFinanceProvider()
session_store = SessionStore()
ma_watch_store = MAWatchStore()
