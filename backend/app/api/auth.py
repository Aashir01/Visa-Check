"""Registration, login and account endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import entitlements, ratelimit
from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import Check, Organization, Role, User, utcnow
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        credits=user.credits,
        org=user.org,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
    _rl: None = Depends(ratelimit.limit_auth),
):
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That email is already registered.")

    org = None
    if payload.organization_name:
        org = Organization(name=payload.organization_name.strip(), plan="free")
        db.add(org)
        db.flush()

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=Role.agency_admin if org else Role.user,
        org_id=org.id if org else None,
        credits=settings.free_checks_per_user,
        # A taste of the paid tier, so the upsell is a demonstration rather
        # than a claim.
        ai_credits=settings.free_ai_credits_per_user,
        last_login_at=utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        user=_user_out(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    _rl: None = Depends(ratelimit.limit_auth),
):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is disabled.")

    user.last_login_at = utcnow()
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        user=_user_out(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return _user_out(user)


@router.get("/account")
def account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Plan, credits and usage for /account."""
    total = db.query(Check).filter(Check.user_id == user.id).count()
    org_total = 0
    seats = 0
    if user.org_id:
        org_total = db.query(Check).filter(Check.org_id == user.org_id).count()
        seats = db.query(User).filter(User.org_id == user.org_id).count()

    return {
        "user": _user_out(user).model_dump(),
        "plan": user.org.plan if user.org else "free",
        "credits": user.credits,
        "org_credits": user.org.credits if user.org else 0,
        "checks_run": total,
        "org_checks_run": org_total,
        "team_seats": seats,
        "retention_days": settings.retention_days,
        "entitlement": entitlements.describe(user),
        "daily_check_limit": settings.rate_limit_checks_per_day,
        "checks_left_today": ratelimit.remaining_today(user.id),
    }
