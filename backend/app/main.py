"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, auth, checks, corridors
from .config import settings
from .db import SessionLocal, init_db

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="VisaGuard API",
    version="1.0.0",
    description=(
        "Document completeness checking for visa applications. "
        "Not immigration advice."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, corridors.router, checks.router, admin.router):
    app.include_router(r, prefix=settings.api_prefix)


@app.on_event("startup")
def _startup() -> None:
    if settings.environment != "development":
        if settings.secret_key == "dev-only-insecure-change-me":
            raise RuntimeError(
                "SECRET_KEY is still the development default. Set a real one before "
                "running outside development — it protects both auth tokens and the "
                "encryption of uploaded passports."
            )
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()

    # Say loudly if the configured OCR engine is not actually usable. It
    # falls back to Tesseract rather than failing, which is the right runtime
    # behaviour but exactly the kind of silent downgrade that goes unnoticed
    # for weeks.
    from .pipeline.ocr import probe_provider

    probe = probe_provider()
    if not probe["ready"]:
        log.warning(
            "OCR_PROVIDER=%s is NOT working — checks are falling back to '%s', "
            "which is markedly worse on phone photos. Reason: %s. Fix it "
            "(pip install paddlepaddle paddleocr, and allow the one-time model "
            "download) or set OCR_PROVIDER=tesseract to make the choice explicit. "
            "Run `python cli.py doctor` for a full diagnosis.",
            probe["requested"], probe["actual"], probe["error"],
        )

    log.info(
        "VisaGuard API ready (env=%s, ocr=%s, llm=%s, worker=%s, free_tier_ai=%s)",
        settings.environment,
        settings.ocr_provider,
        "on" if settings.anthropic_api_key else "off",
        settings.worker_mode,
        settings.free_tier_ai_enabled,
    )


@app.get("/health")
def health():
    from . import queue as jobq
    from .pipeline.ocr import probe_provider

    probe = probe_provider()

    db = SessionLocal()
    try:
        queue_state = jobq.depth(db)
    except Exception:  # noqa: BLE001 - health must not depend on a clean DB
        queue_state = None
    finally:
        db.close()

    return {
        "status": "ok",
        "environment": settings.environment,
        "llm_configured": bool(settings.anthropic_api_key),
        "ocr_provider": settings.ocr_provider,
        # ready=false means checks are silently running on a fallback engine.
        "ocr_provider_ready": probe["ready"],
        "ocr_engine_in_use": probe["actual"],
        "ocr_error": probe["error"],
        "free_tier_ai_enabled": settings.free_tier_ai_enabled,
        "worker_mode": settings.worker_mode,
        "queue": queue_state,
        "retention_days": settings.retention_days,
    }


@app.exception_handler(ValueError)
def _value_error(_request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
