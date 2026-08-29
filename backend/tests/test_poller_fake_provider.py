import asyncio
from datetime import UTC, datetime

import pytest

import app.poller as poller_module
from app.market_data.base import PriceQuote
from app.session import SessionStore


class FakeMarketDataProvider:
    """Scripted prices per ticker, one value consumed per call."""

    def __init__(self, prices: dict[str, list[float]]):
        self._prices = {k: list(v) for k, v in prices.items()}

    def get_price(self, ticker: str) -> PriceQuote:
        value = self._prices[ticker].pop(0)
        return PriceQuote(ticker=ticker, price=value, as_of=datetime.now(UTC))


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.db_path", str(tmp_path / "test.db"))
    store = SessionStore()
    monkeypatch.setattr(poller_module, "session_store", store)
    return store


@pytest.fixture(autouse=True)
def always_trading(monkeypatch):
    monkeypatch.setattr(poller_module, "is_tase_trading_now", lambda now: True)


@pytest.fixture()
def captured_emails(monkeypatch):
    sent = []

    def fake_send(state, pct_a, pct_b, spread):
        sent.append((state.ticker_a, state.ticker_b, spread))

    monkeypatch.setattr(poller_module, "send_alert_email", fake_send)
    return sent


@pytest.mark.asyncio
async def test_threshold_crossing_sends_exactly_one_email(isolated_store, captured_emails, monkeypatch):
    # Baseline both at 100. Tick 1: A +1%, B +0% -> spread 1% (< 2% threshold, no alert).
    # Tick 2: A +3%, B +0% -> spread 3% (>= 2% threshold, alert fires).
    # Tick 3: A +5%, B +0% -> spread 5% (still over threshold, must NOT re-alert).
    fake = FakeMarketDataProvider(
        {
            "AAA.TA": [101.0, 103.0, 105.0],
            "BBB.TA": [100.0, 100.0, 100.0],
        }
    )
    monkeypatch.setattr(poller_module, "market_data_provider", fake)

    await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)

    await poller_module._poll_once()
    state = isolated_store.snapshot()
    assert state.alerted is False
    assert captured_emails == []

    await poller_module._poll_once()
    state = isolated_store.snapshot()
    assert state.alerted is True
    assert len(captured_emails) == 1
    assert captured_emails[0][2] == pytest.approx(3.0)

    await poller_module._poll_once()
    state = isolated_store.snapshot()
    assert state.alerted is True
    assert len(captured_emails) == 1  # no repeat email


@pytest.mark.asyncio
async def test_skips_tick_when_session_not_active(isolated_store, captured_emails, monkeypatch):
    fake = FakeMarketDataProvider({"AAA.TA": [999.0], "BBB.TA": [999.0]})
    monkeypatch.setattr(poller_module, "market_data_provider", fake)

    await poller_module._poll_once()  # idle, should be a no-op
    assert captured_emails == []


@pytest.mark.asyncio
async def test_market_data_unavailable_records_error_and_skips(isolated_store, captured_emails, monkeypatch):
    class FailingProvider:
        def get_price(self, ticker):
            from app.market_data.exceptions import MarketDataUnavailable

            raise MarketDataUnavailable(ticker, "boom")

    monkeypatch.setattr(poller_module, "market_data_provider", FailingProvider())

    await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)
    await poller_module._poll_once()

    state = isolated_store.snapshot()
    assert state.last_poll_error is not None
    assert captured_emails == []
