"""Who gets what.

The free tier runs deterministic checks only. That is not a crippled product —
every checklist, identity, financial, date and photo rule still runs, which is
where most findings come from. What the paid tier adds is the AI review of
free-text letters (invitation, employment, cover), the one judgement code
cannot make.

Keeping the split here, rather than scattered through the API, means the rule
"what does a free check include?" has exactly one answer in the codebase.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import settings
from .models import Organization, Role, User


@dataclass
class Entitlement:
    """The outcome of asking "may this user run this check, and with AI?"."""

    allowed: bool
    ai_enabled: bool
    tier: str                      # free | paid | admin
    reason: str = ""
    spend_check_credit: bool = False
    spend_ai_credit: bool = False
    spend_from_org: bool = False


def verification_is_free(db, check) -> bool:
    """Is this re-check a free confirmation of a fix?

    Charging again to confirm the fixes we ourselves asked for breaks the loop
    the product is actually for: nobody gets a file right first time, and a
    person who has just spent an evening rebuilding their bundle should not hit
    a paywall for the answer to "did that work?".

    So each check grants exactly one free child, up to a small chain depth. The
    per-parent limit stops an endless free chain; the depth limit stops a long
    one. A second attempt at the same parent is charged normally.
    """
    from .models import Check, CheckStatus  # local: entitlements imports early

    parent_id = getattr(check, "parent_check_id", None)
    if not parent_id:
        return False

    # One free child per parent — the first re-check, not every re-check.
    # Only siblings that were actually started count; an abandoned draft must
    # not consume someone's free confirmation.
    siblings = (
        db.query(Check)
        .filter(
            Check.parent_check_id == parent_id,
            Check.id != check.id,
            Check.status != CheckStatus.draft,
        )
        .count()
    )
    if siblings:
        return False

    # Walk up the chain so a chain of free re-checks cannot run forever.
    depth, node = 0, check
    while node and node.parent_check_id and depth <= settings.free_recheck_depth:
        node = db.get(Check, node.parent_check_id)
        depth += 1
    return depth <= settings.free_recheck_depth


def is_paid_plan(org: Organization | None) -> bool:
    return bool(org and org.plan in settings.paid_plan_set)


def evaluate(user: User) -> Entitlement:
    """Decide entitlement without mutating anything.

    Call :func:`consume` afterwards to actually spend the credits, so a caller
    can check entitlement (for display) without charging for it.
    """
    org = user.org

    if user.role == Role.admin:
        return Entitlement(True, True, "admin", "admin account")

    # A paid plan gets AI on every check and does not burn AI credits.
    if is_paid_plan(org):
        has_check = user.credits > 0 or org.credits > 0
        if not has_check:
            return Entitlement(
                False, False, "paid", "no checks remaining on this plan"
            )
        return Entitlement(
            True, True, "paid", "paid plan",
            spend_check_credit=True,
            spend_from_org=user.credits <= 0,
        )

    # Free plan: a check is always deterministic unless the user still holds
    # an AI credit, or the deployment has opted the whole free tier into AI.
    has_check = user.credits > 0 or (org and org.credits > 0)
    if not has_check:
        return Entitlement(False, False, "free", "no checks remaining")

    ai = settings.free_tier_ai_enabled or user.ai_credits > 0
    return Entitlement(
        True,
        ai,
        "free",
        "free tier" + ("" if ai else " — deterministic checks only"),
        spend_check_credit=True,
        spend_ai_credit=ai and not settings.free_tier_ai_enabled,
        spend_from_org=user.credits <= 0,
    )


def consume(db, user: User, ent: Entitlement) -> None:
    """Spend whatever the entitlement said it would."""
    if not ent.allowed:
        return

    if ent.spend_check_credit:
        if ent.spend_from_org and user.org and user.org.credits > 0:
            user.org.credits -= 1
        elif user.credits > 0:
            user.credits -= 1

    if ent.spend_ai_credit and user.ai_credits > 0:
        user.ai_credits -= 1

    db.commit()


def refund(db, user: User, ent: Entitlement) -> None:
    """Give back what a failed run consumed."""
    if not ent.allowed:
        return
    if ent.spend_check_credit:
        if ent.spend_from_org and user.org:
            user.org.credits += 1
        else:
            user.credits += 1
    if ent.spend_ai_credit:
        user.ai_credits += 1
    db.commit()


def describe(user: User) -> dict:
    """What the account page and upload screen should tell the user."""
    ent = evaluate(user)
    org = user.org
    return {
        "tier": ent.tier,
        "plan": org.plan if org else "free",
        "checks_remaining": user.credits + (org.credits if org else 0),
        "ai_credits_remaining": user.ai_credits,
        "ai_included": ent.ai_enabled,
        "ai_always_included": is_paid_plan(org) or user.role == Role.admin,
        "reason": ent.reason,
    }
