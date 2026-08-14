"""Refusal decoding: upload a refusal letter, get a recovery plan.

This is the second half of the product. A check tells you what is wrong before
you submit; this tells you what to do after a refusal — and links the two, so a
decoded refusal can be turned straight into a targeted re-check.

It is also the evidence loop. Every decoded refusal is compared against the
check that preceded it, recording which grounds our rules caught and which they
missed. That comparison is the only honest way to know whether the rule packs
work.
"""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from .. import entitlements, ratelimit, refusal as refusal_mod, storage
from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import Check, Corridor, Refusal, Role, RulePack, User, utcnow
from ..pipeline.llm import LlmClient, LlmUsage
from ..pipeline.ocr import get_provider
from ..schemas import RefusalOut, RefusalSummaryOut

log = logging.getLogger(__name__)
router = APIRouter(prefix="/refusals", tags=["refusals"])

ALLOWED_MIMES = {
    "application/pdf", "image/jpeg", "image/jpg", "image/png", "image/webp",
}


def _owned(refusal_id: str, db: Session, user: User) -> Refusal:
    row = db.get(Refusal, refusal_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Refusal not found")
    if user.role == Role.admin or row.user_id == user.id:
        return row
    if user.org_id and row.org_id == user.org_id:
        return row
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Refusal not found")


def _out(db: Session, row: Refusal) -> RefusalOut:
    corridor = db.get(Corridor, row.corridor_id) if row.corridor_id else None
    return RefusalOut(
        id=row.id,
        corridor_id=row.corridor_id,
        corridor_label=corridor.label if corridor else None,
        check_id=row.check_id,
        recheck_id=row.recheck_id,
        filename=row.filename,
        status=row.status,
        method=row.method,
        ground_codes=row.ground_codes or [],
        decoded=row.decoded,
        plan=row.plan,
        appeal=row.appeal,
        confidence=row.confidence,
        consulate=row.consulate,
        decision_date=row.decision_date,
        caught_by_check=row.caught_by_check,
        missed_by_check=row.missed_by_check,
        created_at=row.created_at,
    )


def _grade_previous_check(db: Session, check_id: str | None, codes: list[str]) -> tuple[list, list]:
    """Did the check we ran beforehand flag what the consulate refused on?

    This is the rule packs' report card. A ground the consulate cited that our
    check passed clean is a gap in the rules, and it is far more informative
    than any amount of internal testing.
    """
    if not check_id or not codes:
        return [], []

    check = db.get(Check, check_id)
    if not check or not check.issues:
        return [], []

    flagged = {i.get("rule_id") for i in (check.issues or []) if i.get("rule_id")}
    caught, missed = [], []
    for code in codes:
        g = refusal_mod.ground(code)
        if not g:
            continue
        overlap = sorted(set(g.rule_ids) & flagged)
        entry = {"code": code, "number": g.number, "rules": overlap}
        (caught if overlap else missed).append(entry)
    return caught, missed


@router.get("/grounds")
def refusal_grounds():
    """The eleven standard grounds, for the manual picker."""
    return {"grounds": refusal_mod.as_catalogue(), "source": refusal_mod.grounds.SOURCE}


@router.post("", response_model=RefusalOut, status_code=201)
async def create_refusal(
    request: Request,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    ground_codes: str | None = Form(None),
    corridor_id: str | None = Form(None),
    check_id: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    _rl: None = Depends(ratelimit.limit_upload),
):
    """Decode a refusal from an uploaded letter, pasted text, or ticked grounds."""
    manual = [c.strip() for c in (ground_codes or "").split(",") if c.strip()]
    if not file and not (text or "").strip() and not manual:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Upload your refusal letter, paste its text, or select the grounds "
            "that were ticked.",
        )

    row = Refusal(
        user_id=user.id,
        org_id=user.org_id,
        corridor_id=corridor_id,
        check_id=check_id,
    )
    db.add(row)
    db.flush()

    extracted = (text or "").strip()

    # --- read the uploaded letter ---
    if file is not None:
        mime = (file.content_type or "").lower()
        if mime not in ALLOWED_MIMES:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "Refusal letters must be a PDF, JPG, PNG or WebP.",
            )
        raw = await file.read()
        if not raw:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That file is empty.")
        if len(raw) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"That file exceeds the {settings.max_upload_mb} MB limit.",
            )

        row.filename = (file.filename or "refusal")[:400]
        path, _digest = storage.save_document(row.id, row.id, raw)
        row.storage_path = path

        suffix = ".pdf" if mime == "application/pdf" else ".jpg"
        try:
            with storage.materialise(path, suffix=suffix) as tmp:
                extracted = get_provider().extract(tmp, mime).text or extracted
        except Exception as exc:  # noqa: BLE001 - never lose the record to OCR
            log.warning("refusal OCR failed for %s: %s", row.id, exc)

    row.text_excerpt = extracted[:4000] or None

    # --- decode ---
    usage = LlmUsage()
    if manual:
        decoded = refusal_mod.from_manual(manual)
    else:
        ent = entitlements.evaluate(user)
        llm = LlmClient(usage=usage, enabled=ent.ai_enabled)
        decoded = refusal_mod.decode(extracted, llm=llm)

    pack = None
    if corridor_id:
        corridor = db.get(Corridor, corridor_id)
        if corridor and corridor.active_rulepack_id:
            rp = db.get(RulePack, corridor.active_rulepack_id)
            pack = rp.data if rp else None

    row.method = decoded.method
    row.ground_codes = decoded.codes
    row.confidence = decoded.confidence
    row.consulate = decoded.consulate
    row.decision_date = decoded.decision_date
    row.decoded = {
        "grounds": [g.__dict__ for g in decoded.grounds],
        "notes": decoded.notes,
    }
    row.plan = refusal_mod.build(decoded, pack)
    row.appeal = refusal_mod.appeal_guidance(decoded)
    row.status = "decoded" if decoded.grounds else "undecoded"
    row.llm_cost_usd = usage.usd

    row.caught_by_check, row.missed_by_check = _grade_previous_check(
        db, check_id, decoded.codes
    )

    db.commit()
    db.refresh(row)
    return _out(db, row)


@router.get("", response_model=list[RefusalSummaryOut])
def list_refusals(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Refusal)
    if user.role == Role.admin:
        pass
    elif user.org_id:
        q = q.filter(Refusal.org_id == user.org_id)
    else:
        q = q.filter(Refusal.user_id == user.id)

    corridors = {c.id: c.label for c in db.query(Corridor).all()}
    return [
        RefusalSummaryOut(
            id=r.id,
            corridor_id=r.corridor_id,
            corridor_label=corridors.get(r.corridor_id),
            status=r.status,
            ground_codes=r.ground_codes or [],
            verdict=(r.plan or {}).get("verdict"),
            confidence=r.confidence,
            check_id=r.check_id,
            recheck_id=r.recheck_id,
            created_at=r.created_at,
        )
        for r in q.order_by(Refusal.created_at.desc()).limit(100).all()
    ]


@router.get("/{refusal_id}", response_model=RefusalOut)
def get_refusal(refusal_id: str, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    return _out(db, _owned(refusal_id, db, user))


@router.delete("/{refusal_id}", status_code=204)
def delete_refusal(refusal_id: str, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    row = _owned(refusal_id, db, user)
    storage.purge_check(row.id)
    db.delete(row)
    db.commit()
    return Response(status_code=204)
