"""FastAPI application entry point.

Run locally with: uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import health
from app.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Calling `get_settings()` here enforces the PAPER_TRADING guard and the
    live-endpoint denylist (see app/config.py) -- the app genuinely refuses
    to start (raises RuntimeError) if the configuration is unsafe.
    """
    settings = get_settings()
    app = FastAPI(title="Paper Trading API", version="0.1.0")
    app.state.settings = settings
    app.include_router(health.router)
    return app


app = create_app()
