import pytest

import app.market_data.yfinance_provider as yfinance_provider_module
from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    # Keep tests fast -- the retry delay is real behavior, not something
    # worth actually waiting for in a unit test.
    monkeypatch.setattr(yfinance_provider_module.time, "sleep", lambda seconds: None)


def test_recovers_after_transient_failures(monkeypatch):
    provider = YFinanceProvider()
    attempts = {"count": 0}

    def flaky_fetch(self, ticker):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise MarketDataUnavailable(ticker, "transient blip")
        return 12345.0  # raw agorot; get_price() converts to ILS

    monkeypatch.setattr(YFinanceProvider, "_fetch_price", flaky_fetch)

    quote = provider.get_price("FIBIH.TA")

    assert quote.price == pytest.approx(123.45)
    assert attempts["count"] == 3


def test_gives_up_after_max_attempts(monkeypatch):
    provider = YFinanceProvider()
    attempts = {"count": 0}

    def always_fails(self, ticker):
        attempts["count"] += 1
        raise MarketDataUnavailable(ticker, "still down")

    monkeypatch.setattr(YFinanceProvider, "_fetch_price", always_fails)

    with pytest.raises(MarketDataUnavailable):
        provider.get_price("FIBIH.TA")

    assert attempts["count"] == yfinance_provider_module.MAX_FETCH_ATTEMPTS


def test_succeeds_immediately_without_retry(monkeypatch):
    provider = YFinanceProvider()
    attempts = {"count": 0}

    def always_succeeds(self, ticker):
        attempts["count"] += 1
        return 5000.0  # raw agorot; get_price() converts to ILS

    monkeypatch.setattr(YFinanceProvider, "_fetch_price", always_succeeds)

    quote = provider.get_price("TEVA.TA")

    assert quote.price == pytest.approx(50.0)
    assert attempts["count"] == 1
