from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from app.db import get_connection


class SessionState(BaseModel):
    status: Literal["idle", "active", "stopped"] = "idle"
    ticker_a: str | None = None
    ticker_b: str | None = None
    baseline_price_a: float | None = None
    baseline_price_b: float | None = None
    current_price_a: float | None = None
    current_price_b: float | None = None
    threshold_pct: float | None = None
    alerted: bool = False
    alerted_at: datetime | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    last_updated_at: datetime | None = None
    last_poll_error: str | None = None


def _row_to_state(row) -> SessionState:
    return SessionState(
        status=row["status"],
        ticker_a=row["ticker_a"],
        ticker_b=row["ticker_b"],
        baseline_price_a=row["baseline_price_a"],
        baseline_price_b=row["baseline_price_b"],
        current_price_a=row["current_price_a"],
        current_price_b=row["current_price_b"],
        threshold_pct=row["threshold_pct"],
        alerted=bool(row["alerted"]),
        alerted_at=row["alerted_at"],
        started_at=row["started_at"],
        stopped_at=row["stopped_at"],
        last_updated_at=row["last_updated_at"],
        last_poll_error=row["last_poll_error"],
    )


class SessionStore:
    """Single-session state: an in-memory singleton persisted to a one-row
    SQLite table on every mutation, so an active session survives a backend
    restart. Guarded by an asyncio.Lock shared between the API handlers and
    the poller loop.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self._state = self._load()

    def _load(self) -> SessionState:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM current_session WHERE id = 1").fetchone()
            return _row_to_state(row) if row else SessionState()
        finally:
            conn.close()

    def _persist(self, state: SessionState) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO current_session (
                    id, status, ticker_a, ticker_b,
                    baseline_price_a, baseline_price_b,
                    current_price_a, current_price_b,
                    threshold_pct, alerted, alerted_at,
                    started_at, stopped_at, last_updated_at, last_poll_error
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    ticker_a=excluded.ticker_a,
                    ticker_b=excluded.ticker_b,
                    baseline_price_a=excluded.baseline_price_a,
                    baseline_price_b=excluded.baseline_price_b,
                    current_price_a=excluded.current_price_a,
                    current_price_b=excluded.current_price_b,
                    threshold_pct=excluded.threshold_pct,
                    alerted=excluded.alerted,
                    alerted_at=excluded.alerted_at,
                    started_at=excluded.started_at,
                    stopped_at=excluded.stopped_at,
                    last_updated_at=excluded.last_updated_at,
                    last_poll_error=excluded.last_poll_error
                """,
                (
                    state.status,
                    state.ticker_a,
                    state.ticker_b,
                    state.baseline_price_a,
                    state.baseline_price_b,
                    state.current_price_a,
                    state.current_price_b,
                    state.threshold_pct,
                    int(state.alerted),
                    state.alerted_at.isoformat() if state.alerted_at else None,
                    state.started_at.isoformat() if state.started_at else None,
                    state.stopped_at.isoformat() if state.stopped_at else None,
                    state.last_updated_at.isoformat() if state.last_updated_at else None,
                    state.last_poll_error,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def snapshot(self) -> SessionState:
        return self._state.model_copy()

    async def start_session(self, ticker_a: str, ticker_b: str, threshold_pct: float, price_a: float, price_b: float) -> SessionState:
        async with self.lock:
            if self._state.status == "active":
                raise ValueError("a session is already active")
            now = datetime.now(UTC)
            self._state = SessionState(
                status="active",
                ticker_a=ticker_a,
                ticker_b=ticker_b,
                baseline_price_a=price_a,
                baseline_price_b=price_b,
                current_price_a=price_a,
                current_price_b=price_b,
                threshold_pct=threshold_pct,
                alerted=False,
                started_at=now,
                last_updated_at=now,
            )
            self._persist(self._state)
            return self._state.model_copy()

    async def stop_session(self) -> SessionState:
        async with self.lock:
            if self._state.status != "active":
                raise ValueError("no active session")
            self._state.status = "stopped"
            self._state.stopped_at = datetime.now(UTC)
            self._persist(self._state)
            return self._state.model_copy()

    async def apply_poll_update(
        self,
        *,
        price_a: float | None = None,
        price_b: float | None = None,
        alerted: bool | None = None,
        alerted_at: datetime | None = None,
        last_poll_error: str | None = None,
    ) -> None:
        async with self.lock:
            if self._state.status != "active":
                return
            if price_a is not None:
                self._state.current_price_a = price_a
            if price_b is not None:
                self._state.current_price_b = price_b
            if alerted is not None:
                self._state.alerted = alerted
                self._state.alerted_at = alerted_at
            self._state.last_poll_error = last_poll_error
            self._state.last_updated_at = datetime.now(UTC)
            self._persist(self._state)
