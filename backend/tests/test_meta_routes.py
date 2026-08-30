from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import meta_routes
from app.config import TICKER_PRESETS


def test_list_tickers_returns_full_preset_list():
    app = FastAPI()
    app.include_router(meta_routes.router, prefix="/api")
    client = TestClient(app)

    res = client.get("/api/meta/tickers")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == len(TICKER_PRESETS)
    assert {t["symbol"] for t in body} == {p.symbol for p in TICKER_PRESETS}
