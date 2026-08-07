"""FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, auth, checks, corridors
from .config import settings
from .db import init_db

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
    log.info("VisaGuard API ready (env=%s, ocr=%s, llm=%s)",
             settings.environment, settings.ocr_provider,
             "on" if settings.anthropic_api_key else "off")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": settings.environment,
        "llm_configured": bool(settings.anthropic_api_key),
        "ocr_provider": settings.ocr_provider,
        "retention_days": settings.retention_days,
    }


@app.exception_handler(ValueError)
def _value_error(_request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
