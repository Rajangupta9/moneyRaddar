"""RupeeRadar FastAPI application entrypoint.

Phase 0 scaffolding: health check + CORS. Pipeline routes (`/api/analyze`,
etc.) are added from Phase 1 onward.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .models import HealthResponse

app = FastAPI(
    title="RupeeRadar API",
    description="AI-powered personal finance assistant — backend.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness + config probe used by the frontend shell and CI."""
    return HealthResponse(
        status="ok",
        version=__version__,
        llm_model=settings.rupeeradar_llm_model,
        llm_enabled=settings.llm_enabled,
    )
