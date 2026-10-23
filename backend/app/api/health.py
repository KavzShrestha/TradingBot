"""Health check endpoint used for local dev checks and future CI/readiness probes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, str]:
    """Return a simple liveness payload."""
    return {"status": "ok"}
