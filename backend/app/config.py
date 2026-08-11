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
    # "paddleocr"    — default. Self-hosted PP-OCR, robust on phone photos,
    #                  zero marginal cost. Requires paddlepaddle + a one-time
    #                  model download; falls back to Tesseract if unavailable.
    # "tesseract"    — no extra install, but falls off a cliff on phone photos
    # "claude_vision"— best on the worst inputs, costs tokens per page
    # A rule pack can override this per corridor via `ocr.provider`, so you can
    # pay for accuracy only where it earns its keep.
    ocr_provider: str = "paddleocr"
    tesseract_lang: str = "eng"
    paddle_lang: str = "en"
    tesseract_timeout_s: int = 60
    ocr_raster_dpi: int = 200
    # A digital PDF page with at least this many extractable characters skips
    # OCR entirely — free and more accurate than rasterise-then-OCR.
    text_layer_min_chars: int = 180

    # --- LLM ---
    # Provider: "anthropic" (Claude) or "deepseek" (DeepSeek).  Both can be
    # configured at the same time; the active one is selected below.
    llm_provider: str = "anthropic"  # anthropic | deepseek

    # -- Anthropic (Claude) --
    anthropic_api_key: str = ""
    # -- DeepSeek (OpenAI-compatible) --
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    llm_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 4096
    llm_enabled: bool = True
    # Per-check ceiling. The pipeline stops making LLM calls past this and
    # degrades to deterministic-only rather than silently burning margin (§9).
    llm_budget_usd_per_check: float = 0.15
    # USD per million tokens, used for the cost dashboard.
    # Defaults are for Claude Sonnet; override for DeepSeek (~$0.14/$0.28).
    llm_price_in_per_mtok: float = 3.00
    llm_price_out_per_mtok: float = 15.00
    # Documents whose classification or extraction confidence falls below this
    # get the check routed to /admin/reviews.
    low_confidence_threshold: float = 0.55

    # --- product ---
    free_checks_per_user: int = 1
    default_plan: str = "free"

    # --- tiering (§2) ---
    # The free tier runs deterministic checks only, so a free check costs
    # nothing but CPU. That is what makes unbounded free traffic survivable:
    # every checklist, identity, financial, date and photo rule still runs —
    # only the AI review of free-text letters is withheld.
    free_tier_ai_enabled: bool = False
    # New accounts get this many full AI analyses, so people can see what the
    # paid tier actually buys before being asked to pay for it.
    free_ai_credits_per_user: int = 1
    # Plans that always get the AI review.
    paid_plans: str = "starter,agency,white_label"

    # --- abuse controls ---
    # Rate limits are enforced per process. On a single instance that is
    # exact; behind multiple instances treat them as per-instance budgets.
    rate_limit_enabled: bool = True
    rate_limit_checks_per_day: int = 20        # per account
    rate_limit_checks_per_hour_ip: int = 10    # per IP
    rate_limit_uploads_per_hour_ip: int = 120  # per IP
    rate_limit_auth_per_hour_ip: int = 20      # registrations + logins per IP
    max_bundle_mb: int = 60                    # total bytes across one check

    # --- background work ---
    # "inline" runs checks in a FastAPI BackgroundTask — fine for development
    # and low volume. "queue" leaves them for `python worker.py`, which is
    # what keeps a traffic spike from saturating the web process.
    worker_mode: str = "inline"
    worker_poll_seconds: float = 2.0
    worker_concurrency: int = 2
    # A check stuck in `processing` longer than this is considered abandoned
    # by a dead worker and is returned to the queue.
    worker_stale_minutes: int = 15

    @property
    def paid_plan_set(self) -> set[str]:
        return {p.strip() for p in self.paid_plans.split(",") if p.strip()}

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
