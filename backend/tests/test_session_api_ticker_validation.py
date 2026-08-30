from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.session_routes as session_routes
from app.market_data.base import PriceQuote
from app.session import SessionStore


class FakeMarketDataProvider:
    def __init__(self, price: float = 100.0):
        self.price = price

    def get_price(self, ticker: str) -> PriceQuote:
        return PriceQuote(ticker=ticker, price=self.price, as_of=datetime.now(UTC))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.db_path", str(tmp_path / "test.db"))
    isolated_store = SessionStore()
    monkeypatch.setattr(session_routes, "session_store", isolated_store)
    monkeypatch.setattr(session_routes, "market_data_provider", FakeMarketDataProvider())

    app = FastAPI()
    app.include_router(session_routes.router, prefix="/api")
    return TestClient(app)


def test_start_rejects_ticker_not_in_preset_list(client):
    res = client.post(
        "/api/session/start",
        json={"ticker_a": "NOT_A_REAL_TICKER.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    )
    assert res.status_code == 400


def test_start_accepts_a_newly_added_ta125_ticker(client):
    # CAMT.TA (Camtek) is one of the TA-125 additions, not one of the
    # original six presets -- confirms the expanded list is actually usable.
    res = client.post(
        "/api/session/start",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["ticker_a"] == "CAMT.TA"
    assert body["status"] == "active"
