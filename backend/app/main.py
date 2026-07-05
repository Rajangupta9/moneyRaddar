"""RupeeRadar FastAPI application entrypoint.

Phase 0 scaffolding: health check + CORS. Phase 1 adds `POST /api/analyze`,
which runs the CSV pipeline (ingest -> clean -> categorize -> metrics).
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import settings
from .models import AnalyzeResponse, HealthResponse
from .pipeline import run_pipeline

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


@app.post("/api/analyze", response_model=AnalyzeResponse, tags=["pipeline"])
async def analyze(file: UploadFile = File(...)) -> AnalyzeResponse:
    """Collapsed upload+analyze: a CSV in, cleaned transactions + summary out.

    Phase 1 supports CSV only; XLSX/PDF ingest arrives in Phase 5. Recurring
    series and insights stay empty until Phases 3 and 4.
    """
    filename = (file.filename or "").lower()
    if not filename.endswith(".csv"):
        raise HTTPException(status_code=415, detail="Phase 1 supports CSV files only.")

    data = await file.read()
    max_bytes = settings.rupeeradar_max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.rupeeradar_max_upload_mb} MB limit.",
        )

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")

    transactions, summary, _profile = run_pipeline(text)
    if not transactions:
        raise HTTPException(
            status_code=422,
            detail="No transactions could be parsed from the uploaded file.",
        )

    return AnalyzeResponse(
        session_id=str(uuid.uuid4()),
        transactions=transactions,
        summary=summary,
    )
