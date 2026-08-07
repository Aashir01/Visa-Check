"""Application configuration.

Every knob is env-overridable so the same image runs locally on SQLite and in
production on Postgres without a code change.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "VisaGuard"
    environment: str = "development"
    debug: bool = True

    # --- server ---
    api_prefix: str = "/api"
    # Browsers treat localhost and 127.0.0.1 as distinct origins, so allow
    # both by default — otherwise local development fails CORS depending on
    # which host name the developer happens to type.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- database ---
    database_url: str = f"sqlite:///{BASE_DIR / 'visaguard.db'}"

    # --- auth ---
    # Override in production. Startup refuses to boot with the default when
    # environment != development.
    secret_key: str = "dev-only-insecure-change-me"
    access_token_ttl_minutes: int = 60 * 24 * 7

    # --- storage ---
    # Uploads are encrypted at rest (§9) and purged by retention_days.
    storage_dir: Path = BASE_DIR / "storage"
    retention_days: int = 30
    max_upload_mb: int = 15
    max_files_per_check: int = 25

    # --- OCR ---
    # "tesseract" (default, cheap) or "claude_vision" (accurate on phone
    # photos, costs tokens). Per-corridor override lives in the rule pack as
    # `ocr.provider`, so you can pay for vision only where it earns its keep.
    ocr_provider: str = "tesseract"
    tesseract_lang: str = "eng"
    tesseract_timeout_s: int = 60
    ocr_raster_dpi: int = 200
    # A digital PDF page with at least this many extractable characters skips
    # OCR entirely — free and more accurate than rasterise-then-OCR.
    text_layer_min_chars: int = 180

    # --- LLM ---
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 4096
    llm_enabled: bool = True
    # Per-check ceiling. The pipeline stops making LLM calls past this and
    # degrades to deterministic-only rather than silently burning margin (§9).
    llm_budget_usd_per_check: float = 0.15
    # USD per million tokens, used for the cost dashboard.
    llm_price_in_per_mtok: float = 3.00
    llm_price_out_per_mtok: float = 15.00
    # Documents whose classification or extraction confidence falls below this
    # get the check routed to /admin/reviews.
    low_confidence_threshold: float = 0.55

    # --- product ---
    free_checks_per_user: int = 1
    default_plan: str = "free"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fernet_key(self) -> bytes:
        """Derive the at-rest encryption key from secret_key.

        Deriving rather than storing a second secret keeps deployment to one
        variable. Rotating secret_key therefore also orphans stored files —
        which, given the 30-day purge, is an acceptable trade.
        """
        digest = hashlib.sha256(self.secret_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
