from __future__ import annotations

from fastapi import APIRouter

from app.config import TICKER_PRESETS
from app.schemas import TickerPresetResponse

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/tickers", response_model=list[TickerPresetResponse])
async def list_tickers() -> list[TickerPresetResponse]:
    return [TickerPresetResponse(symbol=p.symbol, name=p.name) for p in TICKER_PRESETS]
