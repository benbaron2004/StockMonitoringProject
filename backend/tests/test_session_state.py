from datetime import UTC, datetime

import pytest

from app.session import SessionStore


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.settings.db_path", str(tmp_path / "test.db"))
    return SessionStore()


@pytest.mark.asyncio
async def test_start_session_sets_baseline_and_current_equal(store):
    state = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    assert state.id
    assert state.status == "active"
    assert state.baseline_price_a == state.current_price_a == 100.0
    assert state.baseline_price_b == state.current_price_b == 50.0
    assert state.alerted is False
    assert state.started_at is not None


@pytest.mark.asyncio
async def test_two_sessions_can_run_concurrently(store):
    s1 = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    s2 = await store.start_session("CCC.TA", "DDD.TA", threshold_pct=1.0, price_a=10.0, price_b=10.0)

    assert s1.id != s2.id
    all_ids = {s.id for s in store.list_all()}
    assert all_ids == {s1.id, s2.id}


@pytest.mark.asyncio
async def test_duplicate_ticker_pair_is_allowed(store):
    s1 = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    s2 = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=3.0, price_a=100.0, price_b=50.0)
    assert s1.id != s2.id
    assert len(store.list_all()) == 2


@pytest.mark.asyncio
async def test_stop_raises_keyerror_for_unknown_id(store):
    with pytest.raises(KeyError):
        await store.stop_session("does-not-exist")


@pytest.mark.asyncio
async def test_stop_raises_valueerror_for_already_stopped_session(store):
    state = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    await store.stop_session(state.id)
    with pytest.raises(ValueError):
        await store.stop_session(state.id)


@pytest.mark.asyncio
async def test_apply_poll_update_ignored_when_not_active(store):
    state = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    await store.stop_session(state.id)
    await store.apply_poll_update(state.id, price_a=999.0, price_b=999.0)
    assert store.snapshot(state.id).current_price_a == 100.0


@pytest.mark.asyncio
async def test_apply_poll_update_ignored_for_unknown_session_id(store):
    await store.apply_poll_update("does-not-exist", price_a=999.0, price_b=999.0)
    assert store.snapshot("does-not-exist") is None


@pytest.mark.asyncio
async def test_apply_poll_update_sets_alerted_once(store):
    state = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    now = datetime.now(UTC)
    await store.apply_poll_update(state.id, price_a=103.0, price_b=50.0, alerted=True, alerted_at=now)
    updated = store.snapshot(state.id)
    assert updated.current_price_a == 103.0
    assert updated.alerted is True
    assert updated.alerted_at is not None


@pytest.mark.asyncio
async def test_remove_session_rejects_active_session(store):
    state = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    with pytest.raises(ValueError):
        await store.remove_session(state.id)


@pytest.mark.asyncio
async def test_remove_session_raises_for_unknown_id(store):
    with pytest.raises(KeyError):
        await store.remove_session("does-not-exist")


@pytest.mark.asyncio
async def test_remove_session_deletes_it_and_survives_restart(store):
    state = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    await store.stop_session(state.id)
    await store.remove_session(state.id)

    assert store.snapshot(state.id) is None

    reloaded = SessionStore()
    assert reloaded.snapshot(state.id) is None


@pytest.mark.asyncio
async def test_active_and_stopped_sessions_both_persist_across_restart(store):
    active = await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    stopped = await store.start_session("CCC.TA", "DDD.TA", threshold_pct=1.0, price_a=10.0, price_b=10.0)
    await store.stop_session(stopped.id)

    reloaded = SessionStore()
    ids = {s.id for s in reloaded.list_all()}
    assert ids == {active.id, stopped.id}
    assert reloaded.snapshot(active.id).status == "active"
    assert reloaded.snapshot(stopped.id).status == "stopped"
