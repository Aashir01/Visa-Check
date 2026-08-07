"""Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Profile = Literal["employed", "self_employed", "student", "retired"]


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)
    organization_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class OrgOut(BaseModel):
    id: str
    name: str
    plan: str
    credits: int
    brand_name: str | None = None
    brand_color: str | None = None

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    credits: int
    ai_credits: int = 0
    org: OrgOut | None = None

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------
# corridors & rule packs
# --------------------------------------------------------------------------


class CorridorOut(BaseModel):
    id: str
    key: str
    label: str
    origin_country: str
    destination: str
    visa_type: str
    description: str | None = None
    enabled: bool
    rulepack_version: str | None = None
    rulepack_unverified: bool = True
    profiles: dict[str, str] = {}

    class Config:
        from_attributes = True


class CorridorUpdate(BaseModel):
    enabled: bool | None = None
    label: str | None = None
    description: str | None = None


class RulePackOut(BaseModel):
    id: str
    corridor_id: str
    version: str
    status: str
    unverified: bool
    notes: str | None = None
    data: dict
    created_at: datetime
    published_at: datetime | None = None

    class Config:
        from_attributes = True


class RulePackSummary(BaseModel):
    id: str
    corridor_id: str
    version: str
    status: str
    unverified: bool
    notes: str | None = None
    created_at: datetime
    published_at: datetime | None = None
    is_active: bool = False

    class Config:
        from_attributes = True


class RulePackCreate(BaseModel):
    version: str = Field(min_length=1, max_length=40)
    data: dict
    notes: str | None = None
    unverified: bool = True
    publish: bool = False

    @field_validator("data")
    @classmethod
    def _validate_pack(cls, v: dict) -> dict:
        from .rulepack_schema import validate_pack

        errors = validate_pack(v)
        if errors:
            raise ValueError("; ".join(errors[:8]))
        return v


class RulePackUpdate(BaseModel):
    """Drafts stay editable; published packs are immutable."""

    data: dict | None = None
    notes: str | None = None
    unverified: bool | None = None

    @field_validator("data")
    @classmethod
    def _validate_pack(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        from .rulepack_schema import validate_pack

        errors = validate_pack(v)
        if errors:
            raise ValueError("; ".join(errors[:8]))
        return v


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------


class CheckCreate(BaseModel):
    corridor_id: str
    applicant_profile: Profile = "employed"
    travel_from: str | None = None
    travel_to: str | None = None
    applicant_meta: dict[str, Any] | None = None


class DocumentOut(BaseModel):
    id: str
    filename: str
    mime: str
    size_bytes: int
    doc_type: str | None = None
    doc_type_label: str | None = None
    doc_type_confidence: float | None = None
    doc_type_source: str | None = None
    ocr_engine: str | None = None
    ocr_confidence: float | None = None
    page_count: int | None = None
    extracted: dict | None = None
    image_metrics: dict | None = None

    class Config:
        from_attributes = True


class DocumentTypeOverride(BaseModel):
    doc_type: str


class CheckSummaryOut(BaseModel):
    id: str
    corridor_id: str
    corridor_label: str | None = None
    applicant_profile: str
    status: str
    risk_score: int | None = None
    risk_band: str | None = None
    document_count: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    rulepack_version: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class CheckOut(BaseModel):
    id: str
    corridor_id: str
    corridor_label: str | None = None
    applicant_profile: str
    travel_from: str | None = None
    travel_to: str | None = None
    status: str
    error: str | None = None
    risk_score: int | None = None
    risk_band: str | None = None
    summary: str | None = None
    confidence: float | None = None
    issues: list[dict] | None = None
    extraction: dict | None = None
    rulepack_version: str | None = None
    rulepack_unverified: bool = True
    documents: list[DocumentOut] = []
    documents_purged_at: datetime | None = None
    pack_meta: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class ChecklistPreviewOut(BaseModel):
    """The free tier (§2 Line A): checklist with no API cost."""

    corridor: CorridorOut
    profile: str
    version: str
    unverified: bool
    disclaimer: str
    required_documents: list[dict]
    optional_documents: list[dict]
    key_thresholds: list[dict]


# --------------------------------------------------------------------------
# admin
# --------------------------------------------------------------------------


class ReviewItemOut(BaseModel):
    id: str
    check_id: str
    corridor_id: str
    reason: str
    confidence: float | None = None
    payload: dict | None = None
    status: str
    correction: dict | None = None
    notes: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True


class ReviewResolve(BaseModel):
    correction: dict | None = None
    notes: str | None = None
    rerun: bool = False


class AdminUserOut(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    credits: int
    ai_credits: int = 0
    is_active: bool
    org_name: str | None = None
    check_count: int = 0
    created_at: datetime
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class CreditGrant(BaseModel):
    credits: int = Field(default=0, ge=-10_000, le=10_000)
    # AI credits are granted separately because the free tier is deterministic
    # only — giving someone checks is not the same as giving them AI review.
    ai_credits: int = Field(default=0, ge=-10_000, le=10_000)
    reason: str | None = None


class UserAdminUpdate(BaseModel):
    role: Literal["user", "agency_admin", "admin"] | None = None
    is_active: bool | None = None
    plan: str | None = None


TokenResponse.model_rebuild()
