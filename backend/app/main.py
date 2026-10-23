"""FastAPI application entry point.

Run locally with: uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api import health


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(title="Paper Trading API", version="0.1.0")
    app.include_router(health.router)
    return app


app = create_app()
