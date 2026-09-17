from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class StartMAWatchRequest(BaseModel):
    ticker: str
    short_period: int
    long_period: int

    @model_validator(mode="after")
    def validate_periods(self) -> "StartMAWatchRequest":
        if self.short_period <= 0 or self.long_period <= 0:
            raise ValueError("short_period and long_period must be > 0")
        if self.short_period >= self.long_period:
            raise ValueError("short_period must be less than long_period")
        return self


class MAWatchResponse(BaseModel):
    id: str
    status: Literal["active", "stopped"]
    ticker: str
    short_period: int
    long_period: int
    last_short_ma: float | None = None
    last_long_ma: float | None = None
    relationship: Literal["golden", "death"] | None = None
    last_checked_date: date | None = None
    last_alerted_at: datetime | None = None
    created_at: datetime
    stopped_at: datetime | None = None
    last_check_error: str | None = None
    market_open: bool = False


class ChartPointResponse(BaseModel):
    date: date
    close: float
    short_ma: float
    long_ma: float


class ChartResponse(BaseModel):
    ticker: str
    short_period: int
    long_period: int
    range: Literal["1W", "1M", "3M", "6M", "1Y", "5Y"]
    points: list[ChartPointResponse]
