"""SQLAlchemy models.

Design notes that matter for the product:

* A ``Check`` snapshots the rule pack version it ran against. §9 requires that
  a later rule edit never silently rewrites an old report, so reports are
  reproducible from ``rulepack_version`` alone.
* ``RulePack`` rows are immutable once published; editing creates a new
  version. ``Corridor.active_rulepack_id`` points at the live one.
* Documents keep only an encrypted blob path plus extracted fields. The purge
  job deletes blobs after ``retention_days`` while leaving the report intact.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Coerce a value read back from the database to an aware UTC datetime.

    SQLite has no native timestamp type, so ``DateTime(timezone=True)`` columns
    come back naive there while Postgres returns them aware. Subtracting one
    from :func:`utcnow` therefore raises on SQLite and works on Postgres —
    a difference that only shows up once deployed.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class Role(str, enum.Enum):
    user = "user"
    agency_admin = "agency_admin"
    admin = "admin"


class CheckStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class RulePackStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class Severity(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    plan: Mapped[str] = mapped_column(String(40), default="free")
    credits: Mapped[int] = mapped_column(Integer, default=0)
    ai_credits: Mapped[int] = mapped_column(Integer, default=0)
    # White-label (§2, Line B $199 tier). Report generation reads these.
    brand_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brand_logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    brand_color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="org")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.user)
    org_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    credits: Mapped[int] = mapped_column(Integer, default=0)
    # Full AI analyses remaining. Separate from `credits` because the free
    # tier runs deterministic checks only (§2) — a user can have checks left
    # but no AI left, and the report says which they got.
    ai_credits: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    org: Mapped[Organization | None] = relationship(back_populates="users")
    checks: Mapped[list["Check"]] = relationship(back_populates="user")


class Corridor(Base):
    """A country + visa-type combination, e.g. Schengen short-stay from PK."""

    __tablename__ = "corridors"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    origin_country: Mapped[str] = mapped_column(String(2))  # ISO-3166 alpha-2
    destination: Mapped[str] = mapped_column(String(80))
    visa_type: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    active_rulepack_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    rulepacks: Mapped[list["RulePack"]] = relationship(back_populates="corridor")


class RulePack(Base):
    """An immutable, versioned checklist for one corridor. The moat (§1)."""

    __tablename__ = "rulepacks"
    __table_args__ = (UniqueConstraint("corridor_id", "version", name="uq_pack_ver"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    corridor_id: Mapped[str] = mapped_column(ForeignKey("corridors.id"), index=True)
    version: Mapped[str] = mapped_column(String(40))
    status: Mapped[RulePackStatus] = mapped_column(
        Enum(RulePackStatus), default=RulePackStatus.draft
    )
    # Set true for AI-drafted packs not yet verified against real casework.
    # Reports render a loud banner while this is true.
    unverified: Mapped[bool] = mapped_column(Boolean, default=True)
    data: Mapped[dict] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    corridor: Mapped[Corridor] = relationship(back_populates="rulepacks")


class RulePackAudit(Base):
    """Who changed which rule, and what the change was."""

    __tablename__ = "rulepack_audits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    rulepack_id: Mapped[str] = mapped_column(String(32), index=True)
    corridor_id: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Check(Base):
    __tablename__ = "checks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    org_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    corridor_id: Mapped[str] = mapped_column(ForeignKey("corridors.id"))

    # Snapshot so a later rule edit cannot rewrite this report (§9).
    rulepack_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rulepack_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rulepack_unverified: Mapped[bool] = mapped_column(Boolean, default=True)

    applicant_profile: Mapped[str] = mapped_column(String(40), default="employed")
    applicant_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    travel_from: Mapped[str | None] = mapped_column(String(20), nullable=True)
    travel_to: Mapped[str | None] = mapped_column(String(20), nullable=True)

    status: Mapped[CheckStatus] = mapped_column(
        Enum(CheckStatus), default=CheckStatus.draft, index=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_band: Mapped[str | None] = mapped_column(String(40), nullable=True)
    issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    extraction: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_free: Mapped[bool] = mapped_column(Boolean, default=False)
    # Whether this check was entitled to the AI letter review. Recorded on the
    # check so an old report always explains which tier produced it.
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tier: Mapped[str] = mapped_column(String(20), default="free")

    # Queue bookkeeping, so a worker that dies mid-check does not strand it.
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    documents_purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="checks")
    corridor: Mapped[Corridor] = relationship()
    documents: Mapped[list["Document"]] = relationship(
        back_populates="check", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    check_id: Mapped[str] = mapped_column(
        ForeignKey("checks.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(400))
    mime: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str | None] = mapped_column(String(600), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    doc_type: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    doc_type_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    doc_type_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Applicant/agent may override a misclassification from the upload UI.
    doc_type_override: Mapped[str | None] = mapped_column(String(60), nullable=True)

    ocr_engine: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    check: Mapped[Check] = relationship(back_populates="documents")

    @property
    def effective_type(self) -> str | None:
        return self.doc_type_override or self.doc_type


class ReviewItem(Base):
    """Low-confidence checks queued for manual correction (/admin/reviews)."""

    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    check_id: Mapped[str] = mapped_column(ForeignKey("checks.id"), index=True)
    corridor_id: Mapped[str] = mapped_column(String(32), index=True)
    reason: Mapped[str] = mapped_column(String(200))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    correction: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)


class CostEvent(Base):
    """One row per LLM call, for /admin/costs."""

    __tablename__ = "cost_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    check_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    corridor_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(40))  # extraction | qualitative | vision
    model: Mapped[str] = mapped_column(String(80))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
