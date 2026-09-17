import pandas as pd
import pytest

import app.market_data.yfinance_provider as yfinance_provider_module
from app.market_data.exceptions import MarketDataUnavailable
from app.market_data.yfinance_provider import YFinanceProvider


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    monkeypatch.setattr(yfinance_provider_module.time, "sleep", lambda seconds: None)


def _fake_history_df(num_rows: int, agorot_closes: list[float] | None = None) -> pd.DataFrame:
    closes = agorot_closes if agorot_closes is not None else [10000.0 + i * 10 for i in range(num_rows)]
    index = pd.date_range("2026-01-01", periods=len(closes), freq="D", tz="Asia/Jerusalem")
    return pd.DataFrame({"Close": closes}, index=index)


def test_get_history_converts_agorot_to_ils(monkeypatch):
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            return _fake_history_df(5, agorot_closes=[10000.0, 10100.0, 10200.0, 10300.0, 10940.0])

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    quotes = provider.get_history("TEVA.TA", 5)

    assert [q.price for q in quotes] == pytest.approx([100.0, 101.0, 102.0, 103.0, 109.40])
    assert len(quotes) == 5


def test_get_history_oldest_first(monkeypatch):
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            return _fake_history_df(3)

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    quotes = provider.get_history("TEVA.TA", 3)
    assert quotes[0].as_of < quotes[1].as_of < quotes[2].as_of


def test_get_history_requests_enough_calendar_days_for_large_windows(monkeypatch):
    # Regression test: the buffer formula was originally tuned only against
    # small (<=200-period) requests and, empirically measured against real
    # TASE data, under-requested calendar days for much larger windows (the
    # chart feature's 5Y+lookback ~1760-period requests) -- the real
    # calendar:trading-day ratio runs up to ~1.83 at large windows, worse
    # than a naive weekends-only estimate. This pins the buffer to stay
    # generous enough for that worst observed ratio, with margin.
    provider = YFinanceProvider()
    captured = {}

    class FakeTicker:
        def history(self, **kwargs):
            captured.update(kwargs)
            return _fake_history_df(1760)

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    provider.get_history("TEVA.TA", 1760)

    requested_days = (captured["end"] - captured["start"]).days
    worst_observed_ratio = 1.83
    assert requested_days >= 1760 * worst_observed_ratio


def test_get_history_passes_auto_adjust_true(monkeypatch):
    provider = YFinanceProvider()
    captured = {}

    class FakeTicker:
        def history(self, **kwargs):
            captured.update(kwargs)
            return _fake_history_df(5)

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    provider.get_history("TEVA.TA", 5)
    assert captured["auto_adjust"] is True
    assert captured["interval"] == "1d"


def test_get_history_raises_when_fewer_rows_than_requested(monkeypatch):
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            return _fake_history_df(3)  # only 3 available

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    with pytest.raises(MarketDataUnavailable):
        provider.get_history("TEVA.TA", 10)


def test_get_history_raises_on_empty_result(monkeypatch):
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            return pd.DataFrame({"Close": []})

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    with pytest.raises(MarketDataUnavailable):
        provider.get_history("TEVA.TA", 5)


def test_get_history_retries_transient_failures(monkeypatch):
    provider = YFinanceProvider()
    attempts = {"count": 0}

    class FlakyTicker:
        def history(self, **kwargs):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("transient blip")
            return _fake_history_df(5)

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FlakyTicker())

    quotes = provider.get_history("TEVA.TA", 5)
    assert len(quotes) == 5
    assert attempts["count"] == 3


def test_get_history_takes_the_most_recent_n_rows(monkeypatch):
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            return _fake_history_df(10)

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    quotes = provider.get_history("TEVA.TA", 3)
    assert len(quotes) == 3
    # last 3 of a 10-row ascending series (10000..10090 agorot, step 10)
    assert [q.price for q in quotes] == pytest.approx([100.7, 100.8, 100.9])


def test_get_history_drops_synthetic_dividend_marker_rows_with_nan_close(monkeypatch):
    """Regression test for a real crash: Yahoo sometimes inserts a non-trading
    row on an ex-dividend date (Volume 0, OHLC all NaN, only Dividends set) --
    observed for BIG.TA and BEZQ.TA. A NaN close silently passed the old
    `close <= 0` guard (NaN comparisons are always False) and poisoned every
    downstream moving average from that date onward, which the frontend then
    crashed on when hovering a poisoned point. The row must be dropped, and
    the requested count must still be met from genuinely-valid rows only.
    """
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            df = _fake_history_df(6)
            df.loc[df.index[2], "Close"] = float("nan")  # synthetic dividend-marker row
            return df

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    quotes = provider.get_history("TEVA.TA", 5)

    assert len(quotes) == 5
    assert all(q.price == q.price for q in quotes)  # q.price == q.price is False only for NaN
    # the NaN row (index 2) is dropped entirely, not just skipped in place --
    # so all 5 remaining genuinely-valid rows are returned, oldest first.
    # (_fake_history_df's default closes are agorot: 10000, 10010, ..., converted /100 below.)
    assert [q.price for q in quotes] == pytest.approx([100.0, 100.1, 100.3, 100.4, 100.5])


def test_get_history_raises_when_too_many_rows_are_nan_close(monkeypatch):
    provider = YFinanceProvider()

    class FakeTicker:
        def history(self, **kwargs):
            df = _fake_history_df(5)
            df.loc[df.index[3], "Close"] = float("nan")
            df.loc[df.index[4], "Close"] = float("nan")
            return df

    monkeypatch.setattr(yfinance_provider_module.yf, "Ticker", lambda ticker: FakeTicker())

    with pytest.raises(MarketDataUnavailable):
        provider.get_history("TEVA.TA", 5)
