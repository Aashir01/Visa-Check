"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import Check, Corridor, Role, RulePack, User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = decode_access_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not available")
    return user


def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if creds is None:
        return None
    payload = decode_access_token(creds.credentials)
    if not payload:
        return None
    return db.get(User, payload.get("sub"))


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def owned_check(check_id: str, db: Session, user: User) -> Check:
    """A check is visible to its owner, their org, or an admin."""
    check = db.get(Check, check_id)
    if not check:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Check not found")
    if user.role == Role.admin:
        return check
    if check.user_id == user.id:
        return check
    if user.org_id and check.org_id == user.org_id:
        return check
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Check not found")


def active_pack(db: Session, corridor: Corridor) -> tuple[RulePack, dict]:
    if not corridor.active_rulepack_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Corridor '{corridor.key}' has no published rule pack.",
        )
    pack = db.get(RulePack, corridor.active_rulepack_id)
    if not pack:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Corridor '{corridor.key}' points at a rule pack that no longer exists.",
        )
    return pack, pack.data
