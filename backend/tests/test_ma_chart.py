import math
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.ma.routes as ma_routes
from app.ma.chart import RANGE_TRADING_DAYS, build_chart_points, fetch_periods_needed, trailing_sma
from app.market_data.base import PriceQuote
from app.market_data.exceptions import MarketDataUnavailable


# --- pure logic: trailing_sma -----------------------------------------------


def test_trailing_sma_none_prefix_then_correct_values():
    result = trailing_sma([1.0, 2.0, 3.0, 4.0, 5.0], window=3)
    assert result == [None, None, 2.0, 3.0, 4.0]


def test_trailing_sma_window_one_is_identity():
    result = trailing_sma([1.0, 2.0, 3.0], window=1)
    assert result == [1.0, 2.0, 3.0]


def test_trailing_sma_window_equals_length():
    result = trailing_sma([2.0, 4.0, 6.0], window=3)
    assert result == [None, None, 4.0]


def test_trailing_sma_rejects_non_positive_window():
    with pytest.raises(ValueError):
        trailing_sma([1.0, 2.0], window=0)


def test_trailing_sma_nan_input_poisons_running_sum_forever():
    # Documents the real defect behind the BIG.TA/BEZQ.TA crash: a single NaN
    # close (from a yfinance dividend-marker row) never cancels out of the
    # O(n) running sum, unlike a plain missing value would in a naive
    # per-window recompute. get_history() is the fix (drop such rows before
    # they ever reach here) -- this test just pins the underlying math so a
    # future change to trailing_sma() doesn't reintroduce the same trap.
    result = trailing_sma([1.0, 2.0, float("nan"), 4.0, 5.0, 6.0], window=2)
    assert result[0] is None
    assert result[1] == pytest.approx(1.5)
    assert all(v is not None and math.isnan(v) for v in result[2:])


# --- pure logic: build_chart_points ------------------------------------------


def test_build_chart_points_rejects_non_finite_price_via_assertion():
    # Defense-in-depth: even though get_history() now filters NaN rows at the
    # source, this guards the API's non-nullable short_ma/long_ma contract --
    # a non-finite value must fail loud (a bug, caught here), never silently
    # serialize as a schema-violating JSON null the frontend isn't prepared
    # for (that's exactly what crashed the chart before the fix).
    history = [
        PriceQuote(ticker="TEVA.TA", price=price, as_of=datetime.now(UTC))
        for price in [100.0, 101.0, float("nan"), 103.0, 104.0]
    ]
    with pytest.raises(AssertionError):
        build_chart_points(history, display_days=5, short_period=1, long_period=2)


# --- pure logic: fetch_periods_needed ---------------------------------------


def test_fetch_periods_needed_adds_max_period_lookback():
    assert fetch_periods_needed("1M", short_period=50, long_period=200) == RANGE_TRADING_DAYS["1M"] + 200
    assert fetch_periods_needed("1W", short_period=50, long_period=200) == RANGE_TRADING_DAYS["1W"] + 200


def test_fetch_periods_needed_uses_larger_of_the_two_periods():
    # short_period > long_period would be rejected elsewhere, but the helper
    # itself should just take the max defensively.
    assert fetch_periods_needed("1M", short_period=300, long_period=200) == RANGE_TRADING_DAYS["1M"] + 300


# --- API endpoint ------------------------------------------------------------


class FakeChartProvider:
    def __init__(self, num_rows: int, start_price: float = 100.0):
        self.num_rows = num_rows
        self.start_price = start_price
        self.requested_periods: list[int] = []

    def get_price(self, ticker):
        raise NotImplementedError("not used by the chart endpoint")

    def get_history(self, ticker: str, num_periods: int) -> list[PriceQuote]:
        self.requested_periods.append(num_periods)
        if num_periods > self.num_rows:
            raise MarketDataUnavailable(ticker, f"only {self.num_rows} of {num_periods} requested daily closes available")
        closes = [self.start_price + i for i in range(num_periods)]
        return [PriceQuote(ticker=ticker, price=c, as_of=datetime.now(UTC)) for c in closes]


@pytest.fixture()
def client(monkeypatch):
    app = FastAPI()
    app.include_router(ma_routes.router, prefix="/api")
    return TestClient(app)


def test_chart_rejects_ticker_not_in_preset_list(client, monkeypatch):
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=10000))
    res = client.get("/api/ma-watches/chart", params={"ticker": "NOT_REAL.TA", "short_period": 5, "long_period": 12, "range": "1M"})
    assert res.status_code == 400


def test_chart_rejects_short_period_not_less_than_long(client, monkeypatch):
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=10000))
    res = client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 200, "long_period": 50, "range": "1M"})
    assert res.status_code == 400


def test_chart_rejects_period_above_max(client, monkeypatch):
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=10000))
    res = client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 5, "long_period": 501, "range": "1M"})
    assert res.status_code == 422


def test_chart_rejects_invalid_range(client, monkeypatch):
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=10000))
    res = client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 5, "long_period": 12, "range": "10Y"})
    assert res.status_code == 422


def test_chart_returns_422_on_insufficient_history(client, monkeypatch):
    # Fewer rows available than a 5Y range + 200-day lookback needs.
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=500))
    res = client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200, "range": "5Y"})
    assert res.status_code == 422
    assert "not enough historical data" in res.json()["detail"]


def test_chart_happy_path_shape_and_no_nulls(client, monkeypatch):
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=10000))
    res = client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 5, "long_period": 12, "range": "1M"})
    assert res.status_code == 200
    body = res.json()
    assert body["ticker"] == "TEVA.TA"
    assert body["short_period"] == 5
    assert body["long_period"] == 12
    assert body["range"] == "1M"
    assert len(body["points"]) == RANGE_TRADING_DAYS["1M"]
    assert all(p["short_ma"] is not None and p["long_ma"] is not None for p in body["points"])


def test_chart_requests_display_days_plus_lookback(client, monkeypatch):
    fake = FakeChartProvider(num_rows=10000)
    monkeypatch.setattr(ma_routes, "market_data_provider", fake)
    client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 50, "long_period": 200, "range": "1M"})
    assert fake.requested_periods == [RANGE_TRADING_DAYS["1M"] + 200]


def test_chart_points_are_oldest_first(client, monkeypatch):
    monkeypatch.setattr(ma_routes, "market_data_provider", FakeChartProvider(num_rows=10000, start_price=50.0))
    res = client.get("/api/ma-watches/chart", params={"ticker": "TEVA.TA", "short_period": 5, "long_period": 12, "range": "1W"})
    closes = [p["close"] for p in res.json()["points"]]
    assert closes == sorted(closes)  # our fake generates monotonically increasing closes
