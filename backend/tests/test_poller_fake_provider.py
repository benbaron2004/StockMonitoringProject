from datetime import UTC, datetime

import pytest

import app.poller as poller_module
from app.market_data.base import PriceQuote
from app.market_data.exceptions import MarketDataUnavailable
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
        sent.append((state.id, state.ticker_a, state.ticker_b, spread))

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

    state = await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)

    await poller_module._poll_once()
    assert isolated_store.snapshot(state.id).alerted is False
    assert captured_emails == []

    await poller_module._poll_once()
    assert isolated_store.snapshot(state.id).alerted is True
    assert len(captured_emails) == 1
    assert captured_emails[0][3] == pytest.approx(3.0)

    await poller_module._poll_once()
    assert isolated_store.snapshot(state.id).alerted is True
    assert len(captured_emails) == 1  # no repeat email


@pytest.mark.asyncio
async def test_poll_once_is_a_noop_when_no_sessions_exist(isolated_store, captured_emails, monkeypatch):
    fake = FakeMarketDataProvider({})
    monkeypatch.setattr(poller_module, "market_data_provider", fake)

    await poller_module._poll_once()  # no sessions at all, should be a no-op
    assert captured_emails == []


@pytest.mark.asyncio
async def test_stopped_sessions_are_skipped_in_tick(isolated_store, captured_emails, monkeypatch):
    fake = FakeMarketDataProvider({})  # empty -> any get_price call would KeyError
    monkeypatch.setattr(poller_module, "market_data_provider", fake)

    state = await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)
    await isolated_store.stop_session(state.id)

    await poller_module._poll_once()  # would raise KeyError if the stopped session's tickers were fetched
    assert captured_emails == []


@pytest.mark.asyncio
async def test_market_data_unavailable_records_error_and_skips(isolated_store, captured_emails, monkeypatch):
    class FailingProvider:
        def get_price(self, ticker):
            raise MarketDataUnavailable(ticker, "boom")

    monkeypatch.setattr(poller_module, "market_data_provider", FailingProvider())

    state = await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)
    await poller_module._poll_once()

    assert isolated_store.snapshot(state.id).last_poll_error is not None
    assert captured_emails == []


@pytest.mark.asyncio
async def test_multi_session_tick_isolation(isolated_store, captured_emails, monkeypatch):
    # Session 1 crosses its threshold this tick; session 2 does not.
    fake = FakeMarketDataProvider(
        {
            "AAA.TA": [103.0],
            "BBB.TA": [100.0],
            "CCC.TA": [100.5],
            "DDD.TA": [100.0],
        }
    )
    monkeypatch.setattr(poller_module, "market_data_provider", fake)

    s1 = await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)
    s2 = await isolated_store.start_session("CCC.TA", "DDD.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)

    await poller_module._poll_once()

    updated1 = isolated_store.snapshot(s1.id)
    updated2 = isolated_store.snapshot(s2.id)
    assert updated1.alerted is True
    assert updated2.alerted is False
    assert updated1.current_price_a == 103.0
    assert updated2.current_price_a == 100.5
    assert len(captured_emails) == 1
    assert captured_emails[0][0] == s1.id


@pytest.mark.asyncio
async def test_one_session_fetch_failure_does_not_affect_other_sessions(isolated_store, captured_emails, monkeypatch):
    class PartiallyFailingProvider:
        def __init__(self):
            self._good = FakeMarketDataProvider({"CCC.TA": [105.0], "DDD.TA": [100.0]})

        def get_price(self, ticker):
            if ticker in ("AAA.TA", "BBB.TA"):
                raise MarketDataUnavailable(ticker, "boom")
            return self._good.get_price(ticker)

    monkeypatch.setattr(poller_module, "market_data_provider", PartiallyFailingProvider())

    s1 = await isolated_store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)
    s2 = await isolated_store.start_session("CCC.TA", "DDD.TA", threshold_pct=2.0, price_a=100.0, price_b=100.0)

    await poller_module._poll_once()

    failed = isolated_store.snapshot(s1.id)
    healthy = isolated_store.snapshot(s2.id)
    assert failed.last_poll_error is not None
    assert healthy.last_poll_error is None
    assert healthy.alerted is True
    assert len(captured_emails) == 1
    assert captured_emails[0][0] == s2.id
