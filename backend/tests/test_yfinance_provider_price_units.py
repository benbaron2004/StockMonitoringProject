import pytest

import app.market_data.yfinance_provider as yfinance_provider_module
from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    monkeypatch.setattr(yfinance_provider_module.time, "sleep", lambda seconds: None)


def test_get_price_converts_agorot_to_ils(monkeypatch):
    provider = YFinanceProvider()

    def fake_fetch(self, ticker):
        return 10940.0  # raw agorot, as Yahoo reports it for TASE tickers

    monkeypatch.setattr(YFinanceProvider, "_fetch_price", fake_fetch)

    quote = provider.get_price("TEVA.TA")

    assert quote.price == pytest.approx(109.40)


def test_outlier_check_compares_post_conversion_values(monkeypatch):
    provider = YFinanceProvider()
    calls = {"count": 0}

    def fake_fetch(self, ticker):
        calls["count"] += 1
        # First call: 10000 agorot (100.00 ILS). Second call: 10500 agorot
        # (105.00 ILS) -- a 5% real-terms move, well under the 20% outlier
        # threshold, so it must NOT be rejected once compared in ILS.
        return 10000.0 if calls["count"] == 1 else 10500.0

    monkeypatch.setattr(YFinanceProvider, "_fetch_price", fake_fetch)

    first = provider.get_price("TEVA.TA")
    second = provider.get_price("TEVA.TA")

    assert first.price == pytest.approx(100.0)
    assert second.price == pytest.approx(105.0)


def test_outlier_check_still_rejects_a_real_glitch_in_ils_terms(monkeypatch):
    provider = YFinanceProvider()
    calls = {"count": 0}

    def fake_fetch(self, ticker):
        calls["count"] += 1
        # 100.00 ILS then a bogus 500.00 ILS reading (400% jump) -- must
        # still be rejected after conversion, not just before it.
        return 10000.0 if calls["count"] == 1 else 50000.0

    monkeypatch.setattr(YFinanceProvider, "_fetch_price", fake_fetch)

    provider.get_price("TEVA.TA")
    with pytest.raises(MarketDataUnavailable):
        provider.get_price("TEVA.TA")
