from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Response

from app.config import TICKER_PRESETS
from app.deps import market_data_provider, session_store
from app.market_data.exceptions import MarketDataUnavailable
from app.schemas import SessionResponse, StartSessionRequest
from app.session import SessionState
from app.trading_calendar.tase_calendar import is_tase_trading_now

router = APIRouter(prefix="/sessions", tags=["sessions"])

_VALID_SYMBOLS = {p.symbol for p in TICKER_PRESETS}


def _to_response(state: SessionState) -> SessionResponse:
    pct_a = pct_b = spread = None
    if state.baseline_price_a and state.current_price_a is not None:
        pct_a = (state.current_price_a - state.baseline_price_a) / state.baseline_price_a * 100
    if state.baseline_price_b and state.current_price_b is not None:
        pct_b = (state.current_price_b - state.baseline_price_b) / state.baseline_price_b * 100
    if pct_a is not None and pct_b is not None:
        spread = abs(pct_a - pct_b)

    return SessionResponse(
        id=state.id,
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


@router.post("", status_code=201, response_model=SessionResponse)
async def start_session(req: StartSessionRequest) -> SessionResponse:
    if req.ticker_a not in _VALID_SYMBOLS or req.ticker_b not in _VALID_SYMBOLS:
        raise HTTPException(400, "both tickers must be from the preset list")

    try:
        quote_a = await asyncio.to_thread(market_data_provider.get_price, req.ticker_a)
        quote_b = await asyncio.to_thread(market_data_provider.get_price, req.ticker_b)
    except MarketDataUnavailable as exc:
        raise HTTPException(502, f"could not fetch a starting price: {exc}") from exc

    state = await session_store.start_session(
        req.ticker_a, req.ticker_b, req.threshold_pct, quote_a.price, quote_b.price
    )
    return _to_response(state)


@router.post("/{session_id}/stop", response_model=SessionResponse)
async def stop_session(session_id: str) -> SessionResponse:
    try:
        state = await session_store.stop_session(session_id)
    except KeyError as exc:
        raise HTTPException(404, "no session with that id") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _to_response(state)


@router.delete("/{session_id}", status_code=204)
async def remove_session(session_id: str) -> None:
    try:
        await session_store.remove_session(session_id)
    except KeyError as exc:
        raise HTTPException(404, "no session with that id") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("", response_model=list[SessionResponse])
async def list_sessions(response: Response) -> list[SessionResponse]:
    # This is polled every few seconds and must never be served stale from
    # the browser cache -- a reload mid-session depends on always getting a
    # fresh read here to correctly resume the live view for every card.
    response.headers["Cache-Control"] = "no-store"
    return [_to_response(state) for state in session_store.list_all()]
