from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel

from app.db import get_connection


class SessionState(BaseModel):
    id: str
    status: Literal["active", "stopped"] = "active"
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
        id=row["id"],
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
    """Multiple concurrent named sessions, in-memory, each persisted to its
    own row in SQLite on every mutation so active sessions survive a backend
    restart. Guarded by a single asyncio.Lock shared between the API
    handlers and the poller loop -- contention is negligible at this app's
    scale (a handful of sessions, one user), so per-session locks would add
    real complexity (lock-per-id creation/cleanup) for no measured benefit.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self._sessions: dict[str, SessionState] = self._load_all()

    def _load_all(self) -> dict[str, SessionState]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM sessions ORDER BY started_at ASC").fetchall()
            return {row["id"]: _row_to_state(row) for row in rows}
        finally:
            conn.close()

    def _persist(self, state: SessionState) -> None:
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO sessions (
                    id, status, ticker_a, ticker_b,
                    baseline_price_a, baseline_price_b,
                    current_price_a, current_price_b,
                    threshold_pct, alerted, alerted_at,
                    started_at, stopped_at, last_updated_at, last_poll_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    state.id,
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

    def _delete(self, session_id: str) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def snapshot(self, session_id: str) -> SessionState | None:
        state = self._sessions.get(session_id)
        return state.model_copy() if state else None

    def list_all(self) -> list[SessionState]:
        return [state.model_copy() for state in self._sessions.values()]

    async def start_session(
        self, ticker_a: str, ticker_b: str, threshold_pct: float, price_a: float, price_b: float
    ) -> SessionState:
        async with self.lock:
            now = datetime.now(UTC)
            state = SessionState(
                id=uuid.uuid4().hex,
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
            self._sessions[state.id] = state
            self._persist(state)
            return state.model_copy()

    async def stop_session(self, session_id: str) -> SessionState:
        async with self.lock:
            state = self._sessions.get(session_id)
            if state is None:
                raise KeyError(session_id)
            if state.status != "active":
                raise ValueError("session is not active")
            state.status = "stopped"
            state.stopped_at = datetime.now(UTC)
            self._persist(state)
            return state.model_copy()

    async def remove_session(self, session_id: str) -> None:
        async with self.lock:
            state = self._sessions.get(session_id)
            if state is None:
                raise KeyError(session_id)
            if state.status == "active":
                raise ValueError("stop the session before removing it")
            del self._sessions[session_id]
            self._delete(session_id)

    async def apply_poll_update(
        self,
        session_id: str,
        *,
        price_a: float | None = None,
        price_b: float | None = None,
        alerted: bool | None = None,
        alerted_at: datetime | None = None,
        last_poll_error: str | None = None,
    ) -> None:
        async with self.lock:
            state = self._sessions.get(session_id)
            if state is None or state.status != "active":
                return
            if price_a is not None:
                state.current_price_a = price_a
            if price_b is not None:
                state.current_price_b = price_b
            if alerted is not None:
                state.alerted = alerted
                state.alerted_at = alerted_at
            state.last_poll_error = last_poll_error
            state.last_updated_at = datetime.now(UTC)
            self._persist(state)
