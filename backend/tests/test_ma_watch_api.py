import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.ma.routes as ma_routes
from app.ma.state import MAWatchStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.db_path", str(tmp_path / "test.db"))
    isolated_store = MAWatchStore()
    monkeypatch.setattr(ma_routes, "ma_watch_store", isolated_store)

    app = FastAPI()
    app.include_router(ma_routes.router, prefix="/api")
    return TestClient(app)


def test_start_rejects_ticker_not_in_preset_list(client):
    res = client.post("/api/ma-watches", json={"ticker": "NOT_A_REAL_TICKER.TA", "short_period": 50, "long_period": 200})
    assert res.status_code == 400


def test_start_rejects_short_period_not_less_than_long(client):
    res = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 200, "long_period": 50})
    assert res.status_code == 422


def test_start_succeeds_and_does_not_synchronously_fetch(client):
    res = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200})
    assert res.status_code == 201
    body = res.json()
    assert body["id"]
    assert body["ticker"] == "TEVA.TA"
    assert body["status"] == "active"
    assert body["last_checked_date"] is None
    assert body["relationship"] is None


def test_start_never_returns_409_for_concurrent_watches(client):
    first = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200})
    second = client.post("/api/ma-watches", json={"ticker": "ICL.TA", "short_period": 20, "long_period": 100})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_list_returns_all_watches_including_stopped(client):
    started = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200}).json()
    client.post(f"/api/ma-watches/{started['id']}/stop")

    res = client.get("/api/ma-watches")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["status"] == "stopped"


def test_list_response_has_no_store_cache_header(client):
    res = client.get("/api/ma-watches")
    assert res.headers["cache-control"] == "no-store"


def test_stop_unknown_watch_returns_404(client):
    res = client.post("/api/ma-watches/does-not-exist/stop")
    assert res.status_code == 404


def test_stop_already_stopped_watch_returns_409(client):
    started = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200}).json()
    client.post(f"/api/ma-watches/{started['id']}/stop")
    res = client.post(f"/api/ma-watches/{started['id']}/stop")
    assert res.status_code == 409


def test_remove_stopped_watch_returns_204_and_drops_from_list(client):
    started = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200}).json()
    client.post(f"/api/ma-watches/{started['id']}/stop")

    res = client.delete(f"/api/ma-watches/{started['id']}")
    assert res.status_code == 204
    assert client.get("/api/ma-watches").json() == []


def test_remove_active_watch_returns_409(client):
    started = client.post("/api/ma-watches", json={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200}).json()
    res = client.delete(f"/api/ma-watches/{started['id']}")
    assert res.status_code == 409


def test_remove_unknown_watch_returns_404(client):
    res = client.delete("/api/ma-watches/does-not-exist")
    assert res.status_code == 404
