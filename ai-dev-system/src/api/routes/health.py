"""Health-check route — operational / liveness concern only."""
from fastapi import APIRouter

router = APIRouter(tags=["Ops"])


@router.get("/health")
async def health_check() -> dict:
    """Return service liveness status."""
    return {"status": "ok"}
