from __future__ import annotations

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class TickerPreset(BaseModel):
    symbol: str
    name: str


# Verified against yfinance during build step 1 (scripts/check_ta_prices.py) --
# all six returned a usable price. Edit this list to change what's offered
# in the frontend's ticker pickers.
TICKER_PRESETS: list[TickerPreset] = [
    TickerPreset(symbol="TEVA.TA", name="Teva Pharmaceutical"),
    TickerPreset(symbol="ICL.TA", name="ICL Group"),
    TickerPreset(symbol="NICE.TA", name="NICE Ltd"),
    TickerPreset(symbol="ESLT.TA", name="Elbit Systems"),
    TickerPreset(symbol="POLI.TA", name="Bank Hapoalim"),
    TickerPreset(symbol="LUMI.TA", name="Bank Leumi"),
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    alert_from_email: str = ""
    alert_to_email: str = ""

    poll_interval_seconds: int = 45
    default_threshold_pct: float = 2.0

    db_path: str = "./data/app.db"


settings = Settings()
