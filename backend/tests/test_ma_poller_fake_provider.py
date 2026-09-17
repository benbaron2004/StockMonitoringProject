from datetime import UTC, date, time, timedelta
from datetime import datetime as real_datetime

import pytest

import app.ma.poller as ma_poller_module
from app.ma.state import MAWatchStore
from app.market_data.base import PriceQuote
from app.market_data.exceptions import MarketDataUnavailable
from app.trading_calendar.tase_calendar import TASE_TZ, tase_close_time_for_date

# Real, verified trading Thursday (close 17:14 IDT) and the next trading day
# (Friday, shortened close 13:34 IDT). Real calendar dates, not mocked --
# exercises the actual holidays.py/tase_calendar.py data.
TRADING_THU = date(2026, 9, 17)
TRADING_FRI = date(2026, 9, 18)
NON_TRADING_SAT = date(2026, 9, 19)


class FrozenDatetime(real_datetime):
    """Subclasses real datetime so datetime.combine()/arithmetic used inside
    poller.py keeps working; only now() is overridden to a fixed instant.
    """

    _frozen_utc: real_datetime | None = None

    @classmethod
    def now(cls, tz=None):
        assert cls._frozen_utc is not None
        return cls._frozen_utc.astimezone(tz) if tz is not None else cls._frozen_utc


def freeze_now(monkeypatch, local_dt: real_datetime) -> None:
    """local_dt must be tz-aware, in TASE_TZ (or any tz -- stored as UTC)."""
    FrozenDatetime._frozen_utc = local_dt.astimezone(UTC)
    monkeypatch.setattr(ma_poller_module, "datetime", FrozenDatetime)


def well_after_close(d, monkeypatch, minutes_after=60):
    close_t = tase_close_time_for_date(d)
    assert close_t is not None
    dt = real_datetime.combine(d, close_t, tzinfo=TASE_TZ) + timedelta(minutes=minutes_after)
    freeze_now(monkeypatch, dt)


class FakeMAProvider:
    """Scripted (as_of_date, closes) per ticker, one entry popped per
    get_history() call -- lets a test simulate day-1, day-2, ... ticks.
    """

    def __init__(self, histories: dict[str, list[tuple]]):
        self._histories = {k: list(v) for k, v in histories.items()}
        self.call_log: list[str] = []

    def get_price(self, ticker):
        raise NotImplementedError("not used by the ma poller")

    def get_history(self, ticker: str, num_periods: int) -> list[PriceQuote]:
        self.call_log.append(ticker)
        as_of_date, closes = self._histories[ticker].pop(0)
        trimmed = closes[-num_periods:]
        assert len(trimmed) == num_periods
        as_of = real_datetime.combine(as_of_date, time(17, 14), tzinfo=TASE_TZ)
        return [PriceQuote(ticker=ticker, price=c, as_of=as_of) for c in trimmed]


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.db_path", str(tmp_path / "test.db"))
    store = MAWatchStore()
    monkeypatch.setattr(ma_poller_module, "ma_watch_store", store)
    return store


@pytest.fixture()
def captured_emails(monkeypatch):
    sent = []

    def fake_send(watch, short_ma, long_ma):
        sent.append((watch.id, watch.ticker, watch.last_cross_direction, short_ma, long_ma))

    monkeypatch.setattr(ma_poller_module, "send_ma_alert_email", fake_send)
    return sent


def set_provider(monkeypatch, histories: dict) -> FakeMAProvider:
    fake = FakeMAProvider(histories)
    monkeypatch.setattr(ma_poller_module, "market_data_provider", fake)
    return fake


# closes crafted for short_period=2, long_period=4:
GOLDEN_CLOSES = [10.0, 10.0, 20.0, 20.0]  # long_ma=15, short_ma=20 -> golden
DEATH_CLOSES = [20.0, 20.0, 10.0, 10.0]  # long_ma=15, short_ma=10 -> death
TIE_CLOSES = [10.0, 10.0, 10.0, 10.0]  # long_ma=10, short_ma=10 -> tie


@pytest.mark.asyncio
async def test_first_check_establishes_baseline_without_alerting(isolated_store, captured_emails, monkeypatch):
    watch = await isolated_store.start_watch("TEVA.TA", 2, 4)
    set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES)]})
    well_after_close(TRADING_THU, monkeypatch)

    await ma_poller_module._ma_poll_once()

    updated = isolated_store.snapshot(watch.id)
    assert updated.last_checked_date == TRADING_THU
    assert updated.last_cross_direction == "golden"
    assert captured_emails == []


@pytest.mark.asyncio
async def test_golden_cross_fires_exactly_once(isolated_store, captured_emails, monkeypatch):
    watch = await isolated_store.start_watch("TEVA.TA", 2, 4)
    fake = set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, DEATH_CLOSES), (TRADING_FRI, GOLDEN_CLOSES)]})

    well_after_close(TRADING_THU, monkeypatch)
    await ma_poller_module._ma_poll_once()
    assert captured_emails == []  # baseline day, no alert

    well_after_close(TRADING_FRI, monkeypatch)
    await ma_poller_module._ma_poll_once()

    assert len(captured_emails) == 1
    assert captured_emails[0][2] == "golden"
    updated = isolated_store.snapshot(watch.id)
    assert updated.last_cross_direction == "golden"
    assert updated.last_checked_date == TRADING_FRI
    assert fake.call_log == ["TEVA.TA", "TEVA.TA"]


@pytest.mark.asyncio
async def test_death_cross_fires_exactly_once(isolated_store, captured_emails, monkeypatch):
    await isolated_store.start_watch("TEVA.TA", 2, 4)
    set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES), (TRADING_FRI, DEATH_CLOSES)]})

    well_after_close(TRADING_THU, monkeypatch)
    await ma_poller_module._ma_poll_once()
    well_after_close(TRADING_FRI, monkeypatch)
    await ma_poller_module._ma_poll_once()

    assert len(captured_emails) == 1
    assert captured_emails[0][2] == "death"


@pytest.mark.asyncio
async def test_no_change_is_a_noop(isolated_store, captured_emails, monkeypatch):
    await isolated_store.start_watch("TEVA.TA", 2, 4)
    set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES), (TRADING_FRI, GOLDEN_CLOSES)]})

    well_after_close(TRADING_THU, monkeypatch)
    await ma_poller_module._ma_poll_once()
    well_after_close(TRADING_FRI, monkeypatch)
    await ma_poller_module._ma_poll_once()

    assert captured_emails == []


@pytest.mark.asyncio
async def test_tie_holds_previous_state(isolated_store, captured_emails, monkeypatch):
    watch = await isolated_store.start_watch("TEVA.TA", 2, 4)
    set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES), (TRADING_FRI, TIE_CLOSES)]})

    well_after_close(TRADING_THU, monkeypatch)
    await ma_poller_module._ma_poll_once()
    well_after_close(TRADING_FRI, monkeypatch)
    await ma_poller_module._ma_poll_once()

    assert captured_emails == []
    updated = isolated_store.snapshot(watch.id)
    assert updated.last_cross_direction == "golden"  # unchanged by the tie
    assert updated.last_checked_date == TRADING_FRI  # still marked checked today


@pytest.mark.asyncio
async def test_one_watch_failure_does_not_affect_sibling(isolated_store, captured_emails, monkeypatch):
    w1 = await isolated_store.start_watch("TEVA.TA", 2, 4)
    w2 = await isolated_store.start_watch("ICL.TA", 2, 4)

    class PartiallyFailingProvider:
        def get_history(self, ticker, num_periods):
            if ticker == "TEVA.TA":
                raise MarketDataUnavailable(ticker, "boom")
            trimmed = GOLDEN_CLOSES[-num_periods:]
            as_of = real_datetime.combine(TRADING_THU, time(17, 14), tzinfo=TASE_TZ)
            return [PriceQuote(ticker=ticker, price=c, as_of=as_of) for c in trimmed]

    monkeypatch.setattr(ma_poller_module, "market_data_provider", PartiallyFailingProvider())
    well_after_close(TRADING_THU, monkeypatch)

    await ma_poller_module._ma_poll_once()

    failed = isolated_store.snapshot(w1.id)
    healthy = isolated_store.snapshot(w2.id)
    assert failed.last_checked_date is None
    assert failed.last_check_error is not None
    assert healthy.last_checked_date == TRADING_THU
    assert captured_emails == []  # baseline day for the healthy watch too


@pytest.mark.asyncio
async def test_same_day_rerun_does_not_double_fetch_or_fire(isolated_store, captured_emails, monkeypatch):
    await isolated_store.start_watch("TEVA.TA", 2, 4)
    fake = set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES)]})
    well_after_close(TRADING_THU, monkeypatch)

    await ma_poller_module._ma_poll_once()
    await ma_poller_module._ma_poll_once()  # same frozen "today", should skip

    assert fake.call_log == ["TEVA.TA"]  # only the first call actually fetched
    assert captured_emails == []


@pytest.mark.asyncio
async def test_stale_history_defers_instead_of_advancing(isolated_store, captured_emails, monkeypatch):
    watch = await isolated_store.start_watch("TEVA.TA", 2, 4)
    # get_history returns data dated TRADING_THU, but "today" is TRADING_FRI --
    # Yahoo hasn't published Friday's close yet.
    set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES)]})
    well_after_close(TRADING_FRI, monkeypatch)

    await ma_poller_module._ma_poll_once()

    updated = isolated_store.snapshot(watch.id)
    assert updated.last_checked_date is None  # not advanced
    assert updated.last_check_error is not None
    assert captured_emails == []


@pytest.mark.asyncio
async def test_too_early_in_the_day_skips_entirely(isolated_store, captured_emails, monkeypatch):
    await isolated_store.start_watch("TEVA.TA", 2, 4)
    fake = set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES)]})
    # Freeze to right at close, before the configured check-delay has passed.
    close_t = tase_close_time_for_date(TRADING_THU)
    freeze_now(monkeypatch, real_datetime.combine(TRADING_THU, close_t, tzinfo=TASE_TZ))

    await ma_poller_module._ma_poll_once()

    assert fake.call_log == []
    assert captured_emails == []


@pytest.mark.asyncio
async def test_non_trading_day_skips_entirely(isolated_store, captured_emails, monkeypatch):
    await isolated_store.start_watch("TEVA.TA", 2, 4)
    fake = set_provider(monkeypatch, {"TEVA.TA": [(TRADING_THU, GOLDEN_CLOSES)]})
    freeze_now(monkeypatch, real_datetime.combine(NON_TRADING_SAT, time(12, 0), tzinfo=TASE_TZ))

    await ma_poller_module._ma_poll_once()

    assert fake.call_log == []
    assert captured_emails == []
