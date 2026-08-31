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
        "/api/sessions",
        json={"ticker_a": "NOT_A_REAL_TICKER.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    )
    assert res.status_code == 400


def test_start_accepts_a_newly_added_ta125_ticker(client):
    # CAMT.TA (Camtek) is one of the TA-125 additions, not one of the
    # original six presets -- confirms the expanded list is actually usable.
    res = client.post(
        "/api/sessions",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["id"]
    assert body["ticker_a"] == "CAMT.TA"
    assert body["status"] == "active"


def test_start_never_returns_409_for_concurrent_sessions(client):
    first = client.post(
        "/api/sessions",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    )
    second = client.post(
        "/api/sessions",
        json={"ticker_a": "ICL.TA", "ticker_b": "NICE.TA", "threshold_pct": 1.0},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_list_returns_all_sessions_including_stopped(client):
    started = client.post(
        "/api/sessions",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    ).json()
    client.post(f"/api/sessions/{started['id']}/stop")

    res = client.get("/api/sessions")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["status"] == "stopped"


def test_list_response_has_no_store_cache_header(client):
    res = client.get("/api/sessions")
    assert res.headers["cache-control"] == "no-store"


def test_stop_unknown_session_returns_404(client):
    res = client.post("/api/sessions/does-not-exist/stop")
    assert res.status_code == 404


def test_stop_already_stopped_session_returns_409(client):
    started = client.post(
        "/api/sessions",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    ).json()
    client.post(f"/api/sessions/{started['id']}/stop")
    res = client.post(f"/api/sessions/{started['id']}/stop")
    assert res.status_code == 409


def test_remove_stopped_session_returns_204_and_drops_from_list(client):
    started = client.post(
        "/api/sessions",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    ).json()
    client.post(f"/api/sessions/{started['id']}/stop")

    res = client.delete(f"/api/sessions/{started['id']}")
    assert res.status_code == 204
    assert client.get("/api/sessions").json() == []


def test_remove_active_session_returns_409(client):
    started = client.post(
        "/api/sessions",
        json={"ticker_a": "CAMT.TA", "ticker_b": "TEVA.TA", "threshold_pct": 1.0},
    ).json()
    res = client.delete(f"/api/sessions/{started['id']}")
    assert res.status_code == 409


def test_remove_unknown_session_returns_404(client):
    res = client.delete("/api/sessions/does-not-exist")
    assert res.status_code == 404
