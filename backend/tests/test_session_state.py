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
    assert state.status == "active"
    assert state.baseline_price_a == state.current_price_a == 100.0
    assert state.baseline_price_b == state.current_price_b == 50.0
    assert state.alerted is False
    assert state.started_at is not None


@pytest.mark.asyncio
async def test_cannot_start_second_session_while_active(store):
    await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    with pytest.raises(ValueError):
        await store.start_session("CCC.TA", "DDD.TA", threshold_pct=2.0, price_a=10.0, price_b=10.0)


@pytest.mark.asyncio
async def test_cannot_stop_when_not_active(store):
    with pytest.raises(ValueError):
        await store.stop_session()


@pytest.mark.asyncio
async def test_apply_poll_update_ignored_when_not_active(store):
    await store.apply_poll_update(price_a=999.0, price_b=999.0)
    assert store.snapshot().current_price_a is None


@pytest.mark.asyncio
async def test_apply_poll_update_sets_alerted_once(store):
    await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    now = datetime.now(UTC)
    await store.apply_poll_update(price_a=103.0, price_b=50.0, alerted=True, alerted_at=now)
    state = store.snapshot()
    assert state.current_price_a == 103.0
    assert state.alerted is True
    assert state.alerted_at is not None


@pytest.mark.asyncio
async def test_state_persists_across_new_store_instance(store, monkeypatch):
    await store.start_session("AAA.TA", "BBB.TA", threshold_pct=2.0, price_a=100.0, price_b=50.0)
    reloaded = SessionStore()
    assert reloaded.snapshot().status == "active"
    assert reloaded.snapshot().ticker_a == "AAA.TA"
