"""Public corridor listing and the free checklist preview (§2, Line A hook)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import active_pack
from ..models import Corridor, RulePack
from ..pipeline.doctypes import label_for
from ..schemas import ChecklistPreviewOut, CorridorOut

router = APIRouter(prefix="/corridors", tags=["corridors"])


def corridor_out(db: Session, corridor: Corridor) -> CorridorOut:
    version, unverified, profiles = None, True, {}
    if corridor.active_rulepack_id:
        pack = db.get(RulePack, corridor.active_rulepack_id)
        if pack:
            version = pack.version
            unverified = pack.unverified
            profiles = (pack.data or {}).get("profiles") or {}
    return CorridorOut(
        id=corridor.id,
        key=corridor.key,
        label=corridor.label,
        origin_country=corridor.origin_country,
        destination=corridor.destination,
        visa_type=corridor.visa_type,
        description=corridor.description,
        enabled=corridor.enabled,
        rulepack_version=version,
        rulepack_unverified=unverified,
        profiles=profiles,
    )


@router.get("", response_model=list[CorridorOut])
def list_corridors(
    include_disabled: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(Corridor)
    if not include_disabled:
        q = q.filter(Corridor.enabled.is_(True))
    return [corridor_out(db, c) for c in q.order_by(Corridor.label).all()]


@router.get("/{corridor_id}/checklist", response_model=ChecklistPreviewOut)
def checklist(
    corridor_id: str,
    profile: str = Query("employed"),
    db: Session = Depends(get_db),
):
    """The free tier: the full checklist with no OCR and no LLM cost."""
    corridor = db.get(Corridor, corridor_id)
    if not corridor or not corridor.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Corridor not found")

    pack_row, pack = active_pack(db, corridor)

    def applies(spec: dict) -> bool:
        profiles = spec.get("profiles") or ["*"]
        return "*" in profiles or profile in profiles

    required, optional = [], []
    for spec in pack.get("documents", []):
        if not applies(spec):
            continue
        entry = {
            "key": spec.get("key"),
            "label": spec.get("label") or label_for(spec.get("key")),
            "why": spec.get("why"),
            "fix": spec.get("fix"),
            "severity": spec.get("severity", "critical"),
            "alternatives": [label_for(a) for a in (spec.get("satisfied_by") or [])],
        }
        (required if spec.get("required") else optional).append(entry)

    # A handful of headline numbers, so the free tier is genuinely useful.
    thresholds = []
    for rule in pack.get("rules", []):
        p = rule.get("params") or {}
        rtype = rule.get("type")
        if rtype == "financial_sufficiency":
            if p.get("method") == "per_day":
                value = (f"{p.get('per_day_amount')} {p.get('currency', pack.get('currency'))}"
                         f" per day (minimum {p.get('minimum_total', 0)})")
            else:
                value = f"{p.get('amount')} {p.get('currency', pack.get('currency'))}"
            thresholds.append({"label": "Funds expected", "value": value})
        elif rtype == "passport_validity":
            thresholds.append({
                "label": "Passport validity",
                "value": f"at least {p.get('min_days_after_return')} days beyond your return",
            })
        elif rtype == "numeric_min" and p.get("document") == "travel_insurance":
            thresholds.append({
                "label": "Insurance cover",
                "value": f"at least {p.get('min'):,} {p.get('currency', pack.get('currency'))}",
            })
        elif rtype == "statement_history":
            thresholds.append({
                "label": "Bank statement history",
                "value": f"{p.get('min_months')} months",
            })
        elif rtype == "photo_spec":
            thresholds.append({
                "label": "Photograph",
                "value": f"{p.get('width_mm')}mm × {p.get('height_mm')}mm, colour, plain background",
            })

    return ChecklistPreviewOut(
        corridor=corridor_out(db, corridor),
        profile=profile,
        version=pack.get("version", pack_row.version),
        unverified=pack_row.unverified,
        disclaimer=pack.get("disclaimer", ""),
        required_documents=required,
        optional_documents=optional,
        key_thresholds=thresholds,
    )
