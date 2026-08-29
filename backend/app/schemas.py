from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class StartSessionRequest(BaseModel):
    ticker_a: str
    ticker_b: str
    threshold_pct: float

    @model_validator(mode="after")
    def validate_tickers_and_threshold(self) -> "StartSessionRequest":
        if self.ticker_a == self.ticker_b:
            raise ValueError("ticker_a and ticker_b must differ")
        if self.threshold_pct <= 0:
            raise ValueError("threshold_pct must be > 0")
        return self


class SessionStatusResponse(BaseModel):
    status: Literal["idle", "active", "stopped"]
    ticker_a: str | None = None
    ticker_b: str | None = None
    baseline_price_a: float | None = None
    baseline_price_b: float | None = None
    current_price_a: float | None = None
    current_price_b: float | None = None
    pct_change_a: float | None = None
    pct_change_b: float | None = None
    spread_pct: float | None = None
    threshold_pct: float | None = None
    alerted: bool = False
    alerted_at: datetime | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    last_updated_at: datetime | None = None
    market_open: bool = False
    last_poll_error: str | None = None


class TickerPresetResponse(BaseModel):
    symbol: str
    name: str
