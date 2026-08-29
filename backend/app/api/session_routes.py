from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response

from app.config import TICKER_PRESETS
from app.deps import market_data_provider, session_store
from app.market_data.exceptions import MarketDataUnavailable
from app.schemas import SessionStatusResponse, StartSessionRequest
from app.session import SessionState
from app.trading_calendar.tase_calendar import is_tase_trading_now

router = APIRouter(prefix="/session", tags=["session"])

_VALID_SYMBOLS = {p.symbol for p in TICKER_PRESETS}


def _to_response(state: SessionState) -> SessionStatusResponse:
    pct_a = pct_b = spread = None
    if state.baseline_price_a and state.current_price_a is not None:
        pct_a = (state.current_price_a - state.baseline_price_a) / state.baseline_price_a * 100
    if state.baseline_price_b and state.current_price_b is not None:
        pct_b = (state.current_price_b - state.baseline_price_b) / state.baseline_price_b * 100
    if pct_a is not None and pct_b is not None:
        spread = abs(pct_a - pct_b)

    return SessionStatusResponse(
        status=state.status,
        ticker_a=state.ticker_a,
        ticker_b=state.ticker_b,
        baseline_price_a=state.baseline_price_a,
        baseline_price_b=state.baseline_price_b,
        current_price_a=state.current_price_a,
        current_price_b=state.current_price_b,
        pct_change_a=pct_a,
        pct_change_b=pct_b,
        spread_pct=spread,
        threshold_pct=state.threshold_pct,
        alerted=state.alerted,
        alerted_at=state.alerted_at,
        started_at=state.started_at,
        stopped_at=state.stopped_at,
        last_updated_at=state.last_updated_at,
        market_open=is_tase_trading_now(datetime.now(UTC)),
        last_poll_error=state.last_poll_error,
    )


@router.post("/start", status_code=201, response_model=SessionStatusResponse)
async def start_session(req: StartSessionRequest) -> SessionStatusResponse:
    if req.ticker_a not in _VALID_SYMBOLS or req.ticker_b not in _VALID_SYMBOLS:
        raise HTTPException(400, "both tickers must be from the preset list")

    current = session_store.snapshot()
    if current.status == "active":
        raise HTTPException(409, "a session is already active; stop it first")

    try:
        quote_a = await asyncio.to_thread(market_data_provider.get_price, req.ticker_a)
        quote_b = await asyncio.to_thread(market_data_provider.get_price, req.ticker_b)
    except MarketDataUnavailable as exc:
        raise HTTPException(502, f"could not fetch a starting price: {exc}") from exc

    state = await session_store.start_session(
        req.ticker_a, req.ticker_b, req.threshold_pct, quote_a.price, quote_b.price
    )
    return _to_response(state)


@router.post("/stop", response_model=SessionStatusResponse)
async def stop_session() -> SessionStatusResponse:
    try:
        state = await session_store.stop_session()
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _to_response(state)


@router.get("/status", response_model=SessionStatusResponse)
async def get_status(response: Response) -> SessionStatusResponse:
    # This is polled every few seconds and must never be served stale from
    # the browser cache -- a reload mid-session depends on always getting a
    # fresh read here to correctly resume the live view.
    response.headers["Cache-Control"] = "no-store"
    return _to_response(session_store.snapshot())
