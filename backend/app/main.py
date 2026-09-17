from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import meta_routes, session_routes
from app.ma.poller import ma_poller_loop
from app.ma.routes import router as ma_watch_router
from app.poller import poller_loop

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    task = asyncio.create_task(poller_loop())
    ma_task = asyncio.create_task(ma_poller_loop())
    try:
        yield
    finally:
        task.cancel()
        ma_task.cancel()


app = FastAPI(title="TASE Spread Monitor", lifespan=lifespan)

app.include_router(session_routes.router, prefix="/api")
app.include_router(meta_routes.router, prefix="/api")
app.include_router(ma_watch_router, prefix="/api")

_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
