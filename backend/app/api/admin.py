"""Admin surface: dashboard, rules, corridors, reviews, users, costs (§4)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import queue as jobq
from ..config import settings
from ..db import get_db
from ..deps import admin_user
from ..models import (
    Check,
    CheckStatus,
    Corridor,
    CostEvent,
    Document,
    Organization,
    Refusal,
    ReviewItem,
    Role,
    RulePack,
    RulePackAudit,
    RulePackStatus,
    User,
    utcnow,
)
from ..rulepack_schema import validate_pack
from ..schemas import (
    AdminUserOut,
    CorridorOut,
    CorridorUpdate,
    CreditGrant,
    ReviewItemOut,
    ReviewResolve,
    RulePackCreate,
    RulePackOut,
    RulePackSummary,
    RulePackUpdate,
    UserAdminUpdate,
)
from .corridors import corridor_out

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_user)])


# --------------------------------------------------------------------------
# dashboard (/admin)
# --------------------------------------------------------------------------


@router.get("/overview")
def overview(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=days)
    today = utcnow() - timedelta(days=1)

    checks_today = db.query(Check).filter(Check.created_at >= today).count()
    checks_period = db.query(Check).filter(Check.created_at >= since).count()
    completed = (
        db.query(Check)
        .filter(Check.created_at >= since, Check.status == CheckStatus.complete)
        .count()
    )
    failed = (
        db.query(Check)
        .filter(Check.created_at >= since, Check.status == CheckStatus.failed)
        .count()
    )

    spend = (
        db.query(func.coalesce(func.sum(CostEvent.usd), 0.0))
        .filter(CostEvent.created_at >= since)
        .scalar()
    ) or 0.0

    avg_score = (
        db.query(func.avg(Check.risk_score))
        .filter(Check.created_at >= since, Check.risk_score.isnot(None))
        .scalar()
    )
    avg_duration = (
        db.query(func.avg(Check.duration_ms))
        .filter(Check.created_at >= since, Check.duration_ms.isnot(None))
        .scalar()
    )

    return {
        "period_days": days,
        "checks_today": checks_today,
        "checks_period": checks_period,
        "completed": completed,
        "failed": failed,
        "completion_rate": round(completed / checks_period, 3) if checks_period else None,
        "llm_spend_usd": round(float(spend), 4),
        "cost_per_check_usd": round(float(spend) / completed, 4) if completed else None,
        "avg_risk_score": round(float(avg_score), 1) if avg_score is not None else None,
        "avg_duration_ms": int(avg_duration) if avg_duration is not None else None,
        "open_reviews": db.query(ReviewItem).filter(ReviewItem.status == "open").count(),
        "users": db.query(User).count(),
        "organizations": db.query(Organization).count(),
        "corridors_enabled": db.query(Corridor).filter(Corridor.enabled.is_(True)).count(),
        "budget_per_check_usd": settings.llm_budget_usd_per_check,
        "queue": jobq.depth(db),
        "free_tier_ai_enabled": settings.free_tier_ai_enabled,
    }


# --------------------------------------------------------------------------
# corridors (/admin/corridors)
# --------------------------------------------------------------------------


@router.get("/corridors", response_model=list[CorridorOut])
def admin_corridors(db: Session = Depends(get_db)):
    return [corridor_out(db, c) for c in db.query(Corridor).order_by(Corridor.label).all()]


@router.patch("/corridors/{corridor_id}", response_model=CorridorOut)
def update_corridor(
    corridor_id: str, payload: CorridorUpdate, db: Session = Depends(get_db)
):
    corridor = db.get(Corridor, corridor_id)
    if not corridor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Corridor not found")

    if payload.enabled is True and not corridor.active_rulepack_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Publish a rule pack for this corridor before enabling it.",
        )
    for field_name in ("enabled", "label", "description"):
        value = getattr(payload, field_name)
        if value is not None:
            setattr(corridor, field_name, value)
    db.commit()
    return corridor_out(db, corridor)


# --------------------------------------------------------------------------
# rule packs (/admin/rules) — the most important page (§4)
# --------------------------------------------------------------------------


@router.get("/corridors/{corridor_id}/rulepacks", response_model=list[RulePackSummary])
def list_rulepacks(corridor_id: str, db: Session = Depends(get_db)):
    corridor = db.get(Corridor, corridor_id)
    if not corridor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Corridor not found")

    rows = (
        db.query(RulePack)
        .filter(RulePack.corridor_id == corridor_id)
        .order_by(RulePack.created_at.desc())
        .all()
    )
    out = []
    for r in rows:
        summary = RulePackSummary.model_validate(r, from_attributes=True)
        summary.status = r.status.value
        summary.is_active = r.id == corridor.active_rulepack_id
        out.append(summary)
    return out


@router.get("/rulepacks/{rulepack_id}", response_model=RulePackOut)
def get_rulepack(rulepack_id: str, db: Session = Depends(get_db)):
    pack = db.get(RulePack, rulepack_id)
    if not pack:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule pack not found")
    out = RulePackOut.model_validate(pack, from_attributes=True)
    out.status = pack.status.value
    return out


@router.post("/rulepacks/validate")
def validate_rulepack(payload: dict):
    """Dry-run validation so the editor can show errors before saving."""
    errors = validate_pack(payload.get("data") if "data" in payload else payload)
    return {"valid": not errors, "errors": errors}


@router.post("/corridors/{corridor_id}/rulepacks", response_model=RulePackOut, status_code=201)
def create_rulepack(
    corridor_id: str,
    payload: RulePackCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    corridor = db.get(Corridor, corridor_id)
    if not corridor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Corridor not found")

    clash = (
        db.query(RulePack)
        .filter(RulePack.corridor_id == corridor_id, RulePack.version == payload.version)
        .first()
    )
    if clash:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Version '{payload.version}' already exists for this corridor. Versions "
            "are immutable — pick a new version number.",
        )

    data = dict(payload.data)
    data.setdefault("corridor_key", corridor.key)
    data["version"] = payload.version

    pack = RulePack(
        corridor_id=corridor_id,
        version=payload.version,
        data=data,
        notes=payload.notes,
        unverified=payload.unverified,
        created_by=admin.id,
        status=RulePackStatus.draft,
    )
    db.add(pack)
    db.flush()

    db.add(RulePackAudit(
        rulepack_id=pack.id, corridor_id=corridor_id, user_id=admin.id,
        action="create", detail={"version": payload.version},
    ))

    if payload.publish:
        _publish(db, corridor, pack, admin)

    db.commit()
    db.refresh(pack)
    out = RulePackOut.model_validate(pack, from_attributes=True)
    out.status = pack.status.value
    return out


@router.patch("/rulepacks/{rulepack_id}", response_model=RulePackOut)
def update_rulepack(
    rulepack_id: str,
    payload: RulePackUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    pack = db.get(RulePack, rulepack_id)
    if not pack:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule pack not found")
    if pack.status == RulePackStatus.published:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Published rule packs are immutable so that old reports stay reproducible. "
            "Create a new version instead.",
        )

    if payload.data is not None:
        data = dict(payload.data)
        data["version"] = pack.version
        pack.data = data
    if payload.notes is not None:
        pack.notes = payload.notes
    if payload.unverified is not None:
        pack.unverified = payload.unverified

    db.add(RulePackAudit(
        rulepack_id=pack.id, corridor_id=pack.corridor_id, user_id=admin.id,
        action="update", detail={"fields": [k for k, v in payload.model_dump().items()
                                            if v is not None]},
    ))
    db.commit()
    db.refresh(pack)
    out = RulePackOut.model_validate(pack, from_attributes=True)
    out.status = pack.status.value
    return out


def _publish(db: Session, corridor: Corridor, pack: RulePack, admin: User) -> None:
    previous = corridor.active_rulepack_id
    if previous and previous != pack.id:
        old = db.get(RulePack, previous)
        if old:
            old.status = RulePackStatus.archived

    pack.status = RulePackStatus.published
    pack.published_at = utcnow()
    corridor.active_rulepack_id = pack.id

    db.add(RulePackAudit(
        rulepack_id=pack.id, corridor_id=corridor.id, user_id=admin.id,
        action="publish", detail={"version": pack.version, "replaced": previous},
    ))


@router.post("/rulepacks/{rulepack_id}/publish", response_model=RulePackOut)
def publish_rulepack(
    rulepack_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    pack = db.get(RulePack, rulepack_id)
    if not pack:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule pack not found")

    errors = validate_pack(pack.data or {})
    if errors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"message": "This rule pack is not valid.", "errors": errors},
        )

    corridor = db.get(Corridor, pack.corridor_id)
    _publish(db, corridor, pack, admin)
    db.commit()
    db.refresh(pack)
    out = RulePackOut.model_validate(pack, from_attributes=True)
    out.status = pack.status.value
    return out


@router.get("/rulepacks/{rulepack_id}/audit")
def rulepack_audit(rulepack_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(RulePackAudit)
        .filter(RulePackAudit.rulepack_id == rulepack_id)
        .order_by(RulePackAudit.created_at.desc())
        .all()
    )
    users = {u.id: u.email for u in db.query(User).all()}
    return [
        {
            "id": r.id,
            "action": r.action,
            "detail": r.detail,
            "user": users.get(r.user_id),
            "created_at": r.created_at,
        }
        for r in rows
    ]


# --------------------------------------------------------------------------
# review queue (/admin/reviews)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# refusal insights (/admin/refusals)
#
# This is the only honest measure of whether the rule packs work. Internal
# testing tells you the rules do what you wrote; a real refusal tells you
# whether what you wrote was the right thing. A ground the consulate cited that
# our check passed clean is a hole, and it is worth more than any amount of QA.
# --------------------------------------------------------------------------


@router.get("/refusals/insights")
def refusal_insights(
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    from .. import refusal as refusal_mod

    since = utcnow() - timedelta(days=days)
    rows = (
        db.query(Refusal)
        .filter(Refusal.created_at >= since)
        .order_by(Refusal.created_at.desc())
        .all()
    )

    # Only refusals attached to a prior check can grade the rules — the rest
    # still tell us which grounds are common, but not whether we caught them.
    graded = [r for r in rows if r.check_id]

    per_ground: dict[str, dict] = {}
    for r in rows:
        caught = {c["code"] for c in (r.caught_by_check or [])}
        missed = {m["code"] for m in (r.missed_by_check or [])}
        for code in r.ground_codes or []:
            g = refusal_mod.ground(code)
            if not g:
                continue
            entry = per_ground.setdefault(
                code,
                {
                    "code": code,
                    "number": g.number,
                    "plain": g.plain,
                    "category": g.category,
                    "fixable": g.fixable,
                    "cited": 0,
                    "caught": 0,
                    "missed": 0,
                    "rule_ids": list(g.rule_ids),
                },
            )
            entry["cited"] += 1
            if code in caught:
                entry["caught"] += 1
            elif code in missed:
                entry["missed"] += 1

    grounds = []
    for entry in per_ground.values():
        judged = entry["caught"] + entry["missed"]
        entry["catch_rate"] = (
            round(entry["caught"] / judged, 3) if judged else None
        )
        # A ground with no linked rules cannot ever be caught. That is a
        # different problem from a rule that exists and fails to fire, and the
        # admin needs to be able to tell them apart.
        entry["has_rules"] = bool(entry["rule_ids"])
        grounds.append(entry)

    # Worst catch rate first — that is the queue of work.
    grounds.sort(
        key=lambda e: (
            e["catch_rate"] if e["catch_rate"] is not None else 2,
            -e["cited"],
        )
    )

    decoded = [r for r in rows if r.status == "decoded"]
    deterministic = [r for r in decoded if r.method == "deterministic"]

    return {
        "period_days": days,
        "total": len(rows),
        "decoded": len(decoded),
        "undecoded": len(rows) - len(decoded),
        "graded": len(graded),
        # The share decoded without a model call. If this drops, either OCR has
        # regressed or consulates have changed their wording.
        "deterministic_share": (
            round(len(deterministic) / len(decoded), 3) if decoded else None
        ),
        "llm_cost_usd": round(sum(r.llm_cost_usd or 0 for r in rows), 4),
        "grounds": grounds,
        "gaps": [g for g in grounds if g["missed"] > 0],
        "recent": [
            {
                "id": r.id,
                "corridor_id": r.corridor_id,
                "status": r.status,
                "method": r.method,
                "confidence": r.confidence,
                "ground_codes": r.ground_codes or [],
                "missed": [m["number"] for m in (r.missed_by_check or [])],
                "check_id": r.check_id,
                "created_at": r.created_at,
            }
            for r in rows[:50]
        ],
    }


@router.get("/reviews", response_model=list[ReviewItemOut])
def list_reviews(
    status_filter: str = Query("open", alias="status"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ReviewItem)
    if status_filter != "all":
        q = q.filter(ReviewItem.status == status_filter)
    return q.order_by(ReviewItem.created_at.desc()).limit(limit).all()


@router.post("/reviews/{review_id}/resolve", response_model=ReviewItemOut)
def resolve_review(
    review_id: str,
    payload: ReviewResolve,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    """Corrections here become the eval data for future accuracy work (§4)."""
    item = db.get(ReviewItem, review_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review item not found")

    # A correction may re-type documents; apply it before any re-run.
    corrections = (payload.correction or {}).get("document_types") or {}
    for doc_id, doc_type in corrections.items():
        doc = db.get(Document, doc_id)
        if doc and doc.check_id == item.check_id:
            doc.doc_type_override = doc_type
            doc.doc_type = doc_type
            doc.doc_type_confidence = 1.0
            doc.doc_type_source = "admin"

    item.correction = payload.correction
    item.notes = payload.notes
    item.status = "resolved"
    item.resolved_at = utcnow()
    item.resolved_by = admin.id
    db.commit()

    if payload.rerun:
        from ..pipeline.runner import run_check

        check = db.get(Check, item.check_id)
        if check:
            pack = db.get(RulePack, check.rulepack_id)
            if pack:
                run_check(db, check, pack.data or {})

    db.refresh(item)
    return item


# --------------------------------------------------------------------------
# users (/admin/users)
# --------------------------------------------------------------------------


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    q: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        query = query.filter(User.email.ilike(f"%{q}%"))
    users = query.order_by(User.created_at.desc()).limit(limit).all()

    counts = dict(
        db.query(Check.user_id, func.count(Check.id)).group_by(Check.user_id).all()
    )
    orgs = {o.id: o.name for o in db.query(Organization).all()}

    return [
        AdminUserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            credits=u.credits,
            ai_credits=u.ai_credits,
            is_active=u.is_active,
            org_name=orgs.get(u.org_id),
            check_count=counts.get(u.id, 0),
            created_at=u.created_at,
            last_login_at=u.last_login_at,
        )
        for u in users
    ]


@router.post("/users/{user_id}/credits", response_model=AdminUserOut)
def grant_credits(user_id: str, payload: CreditGrant, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.credits = max(0, user.credits + payload.credits)
    if payload.ai_credits:
        user.ai_credits = max(0, user.ai_credits + payload.ai_credits)
    db.commit()
    return AdminUserOut(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role.value,
        credits=user.credits, ai_credits=user.ai_credits, is_active=user.is_active,
        org_name=user.org.name if user.org else None,
        check_count=db.query(Check).filter(Check.user_id == user.id).count(),
        created_at=user.created_at, last_login_at=user.last_login_at,
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: str,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if payload.is_active is False and user.id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "You cannot disable your own account."
        )
    if payload.role and user.id == admin.id and payload.role != "admin":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "You cannot remove your own admin access."
        )

    if payload.role:
        user.role = Role(payload.role)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.plan and user.org:
        user.org.plan = payload.plan
    db.commit()

    return AdminUserOut(
        id=user.id, email=user.email, full_name=user.full_name, role=user.role.value,
        credits=user.credits, ai_credits=user.ai_credits, is_active=user.is_active,
        org_name=user.org.name if user.org else None,
        check_count=db.query(Check).filter(Check.user_id == user.id).count(),
        created_at=user.created_at, last_login_at=user.last_login_at,
    )


# --------------------------------------------------------------------------
# costs (/admin/costs) — kills unprofitable pricing early (§4)
# --------------------------------------------------------------------------


@router.get("/costs")
def costs(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=days)
    corridors = {c.id: c.label for c in db.query(Corridor).all()}

    by_corridor = (
        db.query(
            CostEvent.corridor_id,
            func.count(func.distinct(CostEvent.check_id)),
            func.sum(CostEvent.usd),
            func.sum(CostEvent.tokens_in),
            func.sum(CostEvent.tokens_out),
        )
        .filter(CostEvent.created_at >= since)
        .group_by(CostEvent.corridor_id)
        .all()
    )
    by_kind = (
        db.query(CostEvent.kind, func.count(CostEvent.id), func.sum(CostEvent.usd))
        .filter(CostEvent.created_at >= since)
        .group_by(CostEvent.kind)
        .all()
    )

    # Checks that ran with zero LLM spend still count in the denominator —
    # otherwise cost-per-check looks worse than it is.
    total_checks = (
        db.query(Check)
        .filter(Check.created_at >= since, Check.status == CheckStatus.complete)
        .count()
    )
    total_usd = float(
        db.query(func.coalesce(func.sum(CostEvent.usd), 0.0))
        .filter(CostEvent.created_at >= since).scalar() or 0.0
    )

    priciest = (
        db.query(Check.id, Check.corridor_id, Check.llm_cost_usd, Check.created_at)
        .filter(Check.created_at >= since, Check.llm_cost_usd > 0)
        .order_by(Check.llm_cost_usd.desc())
        .limit(10)
        .all()
    )

    return {
        "period_days": days,
        "total_usd": round(total_usd, 4),
        "checks_completed": total_checks,
        "cost_per_check_usd": round(total_usd / total_checks, 4) if total_checks else None,
        "budget_per_check_usd": settings.llm_budget_usd_per_check,
        "price_in_per_mtok": settings.llm_price_in_per_mtok,
        "price_out_per_mtok": settings.llm_price_out_per_mtok,
        "by_corridor": [
            {
                "corridor_id": cid,
                "corridor": corridors.get(cid, "—"),
                "checks": checks,
                "usd": round(float(usd or 0), 4),
                "usd_per_check": round(float(usd or 0) / checks, 4) if checks else None,
                "tokens_in": int(ti or 0),
                "tokens_out": int(to or 0),
            }
            for cid, checks, usd, ti, to in by_corridor
        ],
        "by_kind": [
            {"kind": kind, "calls": calls, "usd": round(float(usd or 0), 4)}
            for kind, calls, usd in by_kind
        ],
        "most_expensive_checks": [
            {
                "check_id": cid,
                "corridor": corridors.get(corr, "—"),
                "usd": round(float(usd or 0), 4),
                "created_at": created,
            }
            for cid, corr, usd, created in priciest
        ],
    }


@router.post("/purge")
def purge_now(db: Session = Depends(get_db)):
    """Run the retention purge on demand (§9)."""
    from ..storage import purge_expired

    return purge_expired(db)
