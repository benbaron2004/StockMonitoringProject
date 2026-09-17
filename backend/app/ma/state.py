from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel

from app.db import get_connection


class MAWatchState(BaseModel):
    id: str
    status: Literal["active", "stopped"] = "active"
    ticker: str
    short_period: int
    long_period: int
    last_cross_direction: Literal["golden", "death"] | None = None
    last_short_ma: float | None = None
    last_long_ma: float | None = None
    last_checked_date: date | None = None
    last_alerted_at: datetime | None = None
    created_at: datetime
    stopped_at: datetime | None = None
    last_check_error: str | None = None


def _row_to_state(row) -> MAWatchState:
    return MAWatchState(
        id=row["id"],
        status=row["status"],
        ticker=row["ticker"],
        short_period=row["short_period"],
        long_period=row["long_period"],
        last_cross_direction=row["last_cross_direction"],
        last_short_ma=row["last_short_ma"],
        last_long_ma=row["last_long_ma"],
        last_checked_date=row["last_checked_date"],
        last_alerted_at=row["last_alerted_at"],
        created_at=row["created_at"],
        stopped_at=row["stopped_at"],
        last_check_error=row["last_check_error"],
    )


class MAWatchStore:
    """Moving-average watches: independent of, and persisted separately
    from, pair-spread sessions (own SQLite table, own in-memory dict). Same
    concurrency model as SessionStore -- one asyncio.Lock guarding the whole
    dict, negligible contention at this app's scale -- but a deliberately
    separate class/table so this feature never touches pair-spread code.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self._watches: dict[str, MAWatchState] = self._load_all()

    def _load_all(self) -> dict[str, MAWatchState]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM ma_watches ORDER BY created_at ASC").fetchall()
            return {row["id"]: _row_to_state(row) for row in rows}
        finally:
            conn.close()

    def _persist(self, watch: MAWatchState) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO ma_watches (
                    id, status, ticker, short_period, long_period,
                    last_cross_direction, last_short_ma, last_long_ma,
                    last_checked_date, last_alerted_at,
                    created_at, stopped_at, last_check_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    ticker=excluded.ticker,
                    short_period=excluded.short_period,
                    long_period=excluded.long_period,
                    last_cross_direction=excluded.last_cross_direction,
                    last_short_ma=excluded.last_short_ma,
                    last_long_ma=excluded.last_long_ma,
                    last_checked_date=excluded.last_checked_date,
                    last_alerted_at=excluded.last_alerted_at,
                    created_at=excluded.created_at,
                    stopped_at=excluded.stopped_at,
                    last_check_error=excluded.last_check_error
                """,
                (
                    watch.id,
                    watch.status,
                    watch.ticker,
                    watch.short_period,
                    watch.long_period,
                    watch.last_cross_direction,
                    watch.last_short_ma,
                    watch.last_long_ma,
                    watch.last_checked_date.isoformat() if watch.last_checked_date else None,
                    watch.last_alerted_at.isoformat() if watch.last_alerted_at else None,
                    watch.created_at.isoformat(),
                    watch.stopped_at.isoformat() if watch.stopped_at else None,
                    watch.last_check_error,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _delete(self, watch_id: str) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM ma_watches WHERE id = ?", (watch_id,))
            conn.commit()
        finally:
            conn.close()

    def snapshot(self, watch_id: str) -> MAWatchState | None:
        watch = self._watches.get(watch_id)
        return watch.model_copy() if watch else None

    def list_all(self) -> list[MAWatchState]:
        return [watch.model_copy() for watch in self._watches.values()]

    async def start_watch(self, ticker: str, short_period: int, long_period: int) -> MAWatchState:
        async with self.lock:
            watch = MAWatchState(
                id=uuid.uuid4().hex,
                status="active",
                ticker=ticker,
                short_period=short_period,
                long_period=long_period,
                created_at=datetime.now(UTC),
            )
            self._watches[watch.id] = watch
            self._persist(watch)
            return watch.model_copy()

    async def stop_watch(self, watch_id: str) -> MAWatchState:
        async with self.lock:
            watch = self._watches.get(watch_id)
            if watch is None:
                raise KeyError(watch_id)
            if watch.status != "active":
                raise ValueError("watch is not active")
            watch.status = "stopped"
            watch.stopped_at = datetime.now(UTC)
            self._persist(watch)
            return watch.model_copy()

    async def remove_watch(self, watch_id: str) -> None:
        async with self.lock:
            watch = self._watches.get(watch_id)
            if watch is None:
                raise KeyError(watch_id)
            if watch.status == "active":
                raise ValueError("stop the watch before removing it")
            del self._watches[watch_id]
            self._delete(watch_id)

    async def apply_check_result(
        self,
        watch_id: str,
        *,
        checked_date: date,
        short_ma: float,
        long_ma: float,
        cross_direction: Literal["golden", "death"] | None,
        alerted: bool,
        alerted_at: datetime | None = None,
    ) -> None:
        """Record a successful check. Always advances last_checked_date --
        deliberately a separate method from apply_check_error so a failed or
        deferred check can never accidentally advance it (see
        apply_check_error).
        """
        async with self.lock:
            watch = self._watches.get(watch_id)
            if watch is None or watch.status != "active":
                return
            watch.last_checked_date = checked_date
            watch.last_short_ma = short_ma
            watch.last_long_ma = long_ma
            watch.last_cross_direction = cross_direction
            watch.last_check_error = None
            if alerted:
                watch.last_alerted_at = alerted_at
            self._persist(watch)

    async def apply_check_error(self, watch_id: str, error: str) -> None:
        """Record a failed or deferred check. Never advances
        last_checked_date -- the point is that the next poll tick retries
        this watch again today.
        """
        async with self.lock:
            watch = self._watches.get(watch_id)
            if watch is None or watch.status != "active":
                return
            watch.last_check_error = error
            self._persist(watch)
