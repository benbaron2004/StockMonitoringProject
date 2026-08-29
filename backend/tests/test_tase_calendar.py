from datetime import datetime
from zoneinfo import ZoneInfo

from app.trading_calendar.tase_calendar import TASE_TZ, is_tase_trading_now

IL = TASE_TZ


def _at(y, m, d, h, mi, tz=IL):
    return datetime(y, m, d, h, mi, tzinfo=tz)


def test_in_session_weekday():
    # Tuesday 2026-01-06, 12:00 IDT -- normal trading window
    assert is_tase_trading_now(_at(2026, 1, 6, 12, 0)) is True


def test_before_open():
    assert is_tase_trading_now(_at(2026, 1, 6, 9, 0)) is False


def test_after_close_weekday():
    assert is_tase_trading_now(_at(2026, 1, 6, 18, 0)) is False


def test_friday_shortened_hours():
    # Friday 2026-01-09
    assert is_tase_trading_now(_at(2026, 1, 9, 12, 0)) is True
    assert is_tase_trading_now(_at(2026, 1, 9, 14, 0)) is False


def test_sunday_not_a_trading_day():
    # Sunday 2026-01-04 -- TASE no longer trades Sundays as of Jan 5 2026
    assert is_tase_trading_now(_at(2026, 1, 4, 12, 0)) is False


def test_saturday_not_a_trading_day():
    assert is_tase_trading_now(_at(2026, 1, 3, 12, 0)) is False


def test_full_closure_holiday():
    # Independence Day 2026-04-22
    assert is_tase_trading_now(_at(2026, 4, 22, 12, 0)) is False


def test_shortened_session_holiday():
    # Passover interim day 2026-04-03: shortened session 09:59-13:34
    assert is_tase_trading_now(_at(2026, 4, 3, 12, 0)) is True
    assert is_tase_trading_now(_at(2026, 4, 3, 14, 0)) is False


def test_accepts_any_input_timezone():
    # Same instant expressed in UTC should give the same answer as IL-local.
    utc_dt = _at(2026, 1, 6, 12, 0).astimezone(ZoneInfo("UTC"))
    assert is_tase_trading_now(utc_dt) is True


def test_dst_boundary_still_resolves_correctly():
    # Israel DST transitions vary by year; just assert this doesn't raise
    # and resolves to a normal in-session Tuesday regardless of offset.
    assert is_tase_trading_now(_at(2026, 10, 27, 12, 0)) is True
