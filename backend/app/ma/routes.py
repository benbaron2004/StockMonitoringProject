from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from app.config import TICKER_PRESETS
from app.deps import ma_watch_store, market_data_provider
from app.ma.chart import RANGE_TRADING_DAYS, ChartRange, build_chart_points, fetch_periods_needed
from app.ma.schemas import ChartPointResponse, ChartResponse, MAWatchResponse, StartMAWatchRequest
from app.ma.state import MAWatchState
from app.market_data.exceptions import MarketDataUnavailable
from app.trading_calendar.tase_calendar import is_tase_trading_now

router = APIRouter(prefix="/ma-watches", tags=["ma-watches"])

_VALID_SYMBOLS = {p.symbol for p in TICKER_PRESETS}
_MAX_CHART_PERIOD = 500


def _to_response(watch: MAWatchState) -> MAWatchResponse:
    return MAWatchResponse(
        id=watch.id,
        status=watch.status,
        ticker=watch.ticker,
        short_period=watch.short_period,
        long_period=watch.long_period,
        last_short_ma=watch.last_short_ma,
        last_long_ma=watch.last_long_ma,
        relationship=watch.last_cross_direction,
        last_checked_date=watch.last_checked_date,
        last_alerted_at=watch.last_alerted_at,
        created_at=watch.created_at,
        stopped_at=watch.stopped_at,
        last_check_error=watch.last_check_error,
        market_open=is_tase_trading_now(datetime.now(UTC)),
    )


@router.post("", status_code=201, response_model=MAWatchResponse)
async def start_watch(req: StartMAWatchRequest) -> MAWatchResponse:
    if req.ticker not in _VALID_SYMBOLS:
        raise HTTPException(400, "ticker must be from the preset list")

    # Deliberately no synchronous price/history fetch here (unlike pair-spread
    # sessions) -- the daily poller's existing first-check logic establishes
    # the baseline whenever its next eligible pass for this watch occurs.
    watch = await ma_watch_store.start_watch(req.ticker, req.short_period, req.long_period)
    return _to_response(watch)


@router.post("/{watch_id}/stop", response_model=MAWatchResponse)
async def stop_watch(watch_id: str) -> MAWatchResponse:
    try:
        watch = await ma_watch_store.stop_watch(watch_id)
    except KeyError as exc:
        raise HTTPException(404, "no watch with that id") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return _to_response(watch)


@router.delete("/{watch_id}", status_code=204)
async def remove_watch(watch_id: str) -> None:
    try:
        await ma_watch_store.remove_watch(watch_id)
    except KeyError as exc:
        raise HTTPException(404, "no watch with that id") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("", response_model=list[MAWatchResponse])
async def list_watches(response: Response) -> list[MAWatchResponse]:
    response.headers["Cache-Control"] = "no-store"
    return [_to_response(watch) for watch in ma_watch_store.list_all()]


# Stateless -- takes ticker/periods directly rather than a watch id, so it
# serves both an in-progress AddMAWatchForm preview and a persisted watch's
# card identically. NOTE: if a GET /{watch_id} route is ever added, this
# route must stay registered before it (Starlette matches in registration
# order, no automatic static-before-dynamic priority) or "chart" would be
# swallowed as a watch id.
@router.get("/chart", response_model=ChartResponse)
async def get_chart(
    ticker: str,
    short_period: Annotated[int, Query(gt=0, le=_MAX_CHART_PERIOD)],
    long_period: Annotated[int, Query(gt=0, le=_MAX_CHART_PERIOD)],
    chart_range: Annotated[ChartRange, Query(alias="range")],
) -> ChartResponse:
    if ticker not in _VALID_SYMBOLS:
        raise HTTPException(400, "ticker must be from the preset list")
    if short_period >= long_period:
        raise HTTPException(400, "short_period must be less than long_period")

    try:
        history = await asyncio.to_thread(
            market_data_provider.get_history,
            ticker,
            fetch_periods_needed(chart_range, short_period, long_period),
        )
    except MarketDataUnavailable as exc:
        raise HTTPException(
            422, f"not enough historical data for {ticker} to render the {chart_range} range"
        ) from exc

    points = build_chart_points(
        history,
        display_days=RANGE_TRADING_DAYS[chart_range],
        short_period=short_period,
        long_period=long_period,
    )
    return ChartResponse(
        ticker=ticker,
        short_period=short_period,
        long_period=long_period,
        range=chart_range,
        points=[ChartPointResponse(date=p.as_of, close=p.close, short_ma=p.short_ma, long_ma=p.long_ma) for p in points],
    )
