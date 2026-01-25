"""
Health Check Endpoint

Simple health check endpoint for monitoring and load balancers.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "ScholarSync API running"}


