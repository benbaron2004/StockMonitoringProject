from datetime import UTC, date, datetime

import pytest

from app.ma.state import MAWatchStore


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.db_path", str(tmp_path / "test.db"))
    return MAWatchStore()


@pytest.mark.asyncio
async def test_start_watch_defaults(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    assert watch.id
    assert watch.status == "active"
    assert watch.ticker == "TEVA.TA"
    assert watch.short_period == 50
    assert watch.long_period == 200
    assert watch.last_checked_date is None
    assert watch.last_cross_direction is None


@pytest.mark.asyncio
async def test_two_watches_can_run_concurrently(store):
    w1 = await store.start_watch("TEVA.TA", 50, 200)
    w2 = await store.start_watch("ICL.TA", 20, 100)
    ids = {w.id for w in store.list_all()}
    assert ids == {w1.id, w2.id}


@pytest.mark.asyncio
async def test_duplicate_ticker_watches_allowed(store):
    w1 = await store.start_watch("TEVA.TA", 50, 200)
    w2 = await store.start_watch("TEVA.TA", 10, 30)
    assert w1.id != w2.id
    assert len(store.list_all()) == 2


@pytest.mark.asyncio
async def test_stop_raises_keyerror_for_unknown_id(store):
    with pytest.raises(KeyError):
        await store.stop_watch("does-not-exist")


@pytest.mark.asyncio
async def test_stop_raises_valueerror_for_already_stopped(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    await store.stop_watch(watch.id)
    with pytest.raises(ValueError):
        await store.stop_watch(watch.id)


@pytest.mark.asyncio
async def test_remove_rejects_active_watch(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    with pytest.raises(ValueError):
        await store.remove_watch(watch.id)


@pytest.mark.asyncio
async def test_remove_raises_for_unknown_id(store):
    with pytest.raises(KeyError):
        await store.remove_watch("does-not-exist")


@pytest.mark.asyncio
async def test_remove_deletes_and_survives_restart(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    await store.stop_watch(watch.id)
    await store.remove_watch(watch.id)

    assert store.snapshot(watch.id) is None
    reloaded = MAWatchStore()
    assert reloaded.snapshot(watch.id) is None


@pytest.mark.asyncio
async def test_apply_check_result_advances_checked_date(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    await store.apply_check_result(
        watch.id,
        checked_date=date(2026, 9, 17),
        short_ma=110.0,
        long_ma=100.0,
        cross_direction="golden",
        alerted=True,
        alerted_at=datetime.now(UTC),
    )
    updated = store.snapshot(watch.id)
    assert updated.last_checked_date == date(2026, 9, 17)
    assert updated.last_short_ma == 110.0
    assert updated.last_long_ma == 100.0
    assert updated.last_cross_direction == "golden"
    assert updated.last_alerted_at is not None


@pytest.mark.asyncio
async def test_apply_check_error_never_advances_checked_date(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    await store.apply_check_error(watch.id, "boom")
    updated = store.snapshot(watch.id)
    assert updated.last_checked_date is None
    assert updated.last_check_error == "boom"


@pytest.mark.asyncio
async def test_apply_check_result_ignored_when_not_active(store):
    watch = await store.start_watch("TEVA.TA", 50, 200)
    await store.stop_watch(watch.id)
    await store.apply_check_result(
        watch.id, checked_date=date(2026, 9, 17), short_ma=1.0, long_ma=1.0, cross_direction=None, alerted=False
    )
    assert store.snapshot(watch.id).last_checked_date is None


@pytest.mark.asyncio
async def test_apply_check_result_ignored_for_unknown_id(store):
    await store.apply_check_result(
        "does-not-exist", checked_date=date(2026, 9, 17), short_ma=1.0, long_ma=1.0, cross_direction=None, alerted=False
    )
    assert store.snapshot("does-not-exist") is None


@pytest.mark.asyncio
async def test_active_and_stopped_watches_persist_across_restart(store):
    active = await store.start_watch("TEVA.TA", 50, 200)
    stopped = await store.start_watch("ICL.TA", 20, 100)
    await store.stop_watch(stopped.id)

    reloaded = MAWatchStore()
    ids = {w.id for w in reloaded.list_all()}
    assert ids == {active.id, stopped.id}
    assert reloaded.snapshot(active.id).status == "active"
    assert reloaded.snapshot(stopped.id).status == "stopped"
