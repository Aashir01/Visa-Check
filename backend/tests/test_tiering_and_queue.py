"""Tests for the free/paid split, the job queue and abuse controls.

The free tier is what makes unbounded free traffic survivable: a free check
must never make an LLM call, because that is the only part of the pipeline
whose cost scales with volume. These tests pin that.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import entitlements, queue as jobq, ratelimit
from app.config import settings
from app.db import Base
from app.models import Check, CheckStatus, Organization, Role, User, utcnow
from app.pipeline.llm import LlmClient


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def make_user(db, *, credits=5, ai_credits=0, role=Role.user, plan=None):
    org = None
    if plan:
        org = Organization(name="Agency", plan=plan, credits=100)
        db.add(org)
        db.flush()
    user = User(
        email=f"u{utcnow().timestamp()}{credits}{ai_credits}{plan}@example.com",
        password_hash="x",
        role=role,
        credits=credits,
        ai_credits=ai_credits,
        org_id=org.id if org else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------
# entitlements
# --------------------------------------------------------------------------


def test_free_user_without_ai_credits_gets_deterministic_only(db):
    user = make_user(db, credits=3, ai_credits=0)
    ent = entitlements.evaluate(user)
    assert ent.allowed is True
    assert ent.ai_enabled is False, "a free check must not make LLM calls"
    assert ent.tier == "free"


def test_free_user_with_ai_credit_gets_the_full_check(db):
    user = make_user(db, credits=3, ai_credits=1)
    ent = entitlements.evaluate(user)
    assert ent.allowed and ent.ai_enabled and ent.spend_ai_credit


def test_ai_credit_is_spent_once(db):
    user = make_user(db, credits=3, ai_credits=1)
    entitlements.consume(db, user, entitlements.evaluate(user))
    assert user.ai_credits == 0
    assert user.credits == 2
    assert entitlements.evaluate(user).ai_enabled is False


def test_paid_plan_always_gets_ai_without_spending_ai_credits(db):
    user = make_user(db, credits=5, ai_credits=0, plan="agency")
    ent = entitlements.evaluate(user)
    assert ent.ai_enabled is True
    assert ent.spend_ai_credit is False
    entitlements.consume(db, user, ent)
    assert user.ai_credits == 0


def test_user_with_no_checks_is_refused(db):
    user = make_user(db, credits=0, ai_credits=3)
    ent = entitlements.evaluate(user)
    assert ent.allowed is False


def test_org_pool_covers_a_user_with_no_personal_credits(db):
    user = make_user(db, credits=0, plan="agency")
    ent = entitlements.evaluate(user)
    assert ent.allowed and ent.spend_from_org
    entitlements.consume(db, user, ent)
    assert user.org.credits == 99


def test_admin_always_entitled(db):
    user = make_user(db, credits=0, role=Role.admin)
    ent = entitlements.evaluate(user)
    assert ent.allowed and ent.ai_enabled and ent.tier == "admin"


def test_refund_restores_what_was_spent(db):
    user = make_user(db, credits=2, ai_credits=1)
    ent = entitlements.evaluate(user)
    entitlements.consume(db, user, ent)
    entitlements.refund(db, user, ent)
    assert user.credits == 2 and user.ai_credits == 1


def test_global_free_tier_ai_switch(db, monkeypatch):
    user = make_user(db, credits=3, ai_credits=0)
    assert entitlements.evaluate(user).ai_enabled is False
    monkeypatch.setattr(settings, "free_tier_ai_enabled", True)
    ent = entitlements.evaluate(user)
    assert ent.ai_enabled is True
    # The switch must not silently drain credits nobody has.
    assert ent.spend_ai_credit is False


# --------------------------------------------------------------------------
# the client honours the tier
# --------------------------------------------------------------------------


def test_disabled_client_never_calls_the_model(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
    assert LlmClient(enabled=False).available is False
    assert LlmClient(enabled=False).complete(kind="x", system="s", content="c") is None


def test_enabled_client_reports_configured_state(monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    client = LlmClient(enabled=True)
    assert client.configured is False
    assert client.available is False


# --------------------------------------------------------------------------
# queue
# --------------------------------------------------------------------------


def _check(db, user, status=CheckStatus.queued):
    c = Check(user_id=user.id, corridor_id="c1", status=status, applicant_profile="employed")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_claim_returns_a_queued_check_and_marks_it_processing(db):
    user = make_user(db)
    check = _check(db, user)
    claimed = jobq.claim_next(db, "worker-1")
    assert claimed is not None and claimed.id == check.id
    assert claimed.status == CheckStatus.processing
    assert claimed.claimed_by == "worker-1"
    assert claimed.attempts == 1


def test_a_claimed_check_is_not_claimed_twice(db):
    user = make_user(db)
    _check(db, user)
    assert jobq.claim_next(db, "worker-1") is not None
    assert jobq.claim_next(db, "worker-2") is None


def test_claim_returns_none_on_an_empty_queue(db):
    assert jobq.claim_next(db) is None


def test_claims_are_taken_oldest_first(db):
    user = make_user(db)
    first = _check(db, user)
    second = _check(db, user)
    second.created_at = first.created_at + timedelta(minutes=5)
    db.commit()
    assert jobq.claim_next(db).id == first.id


def test_stale_processing_check_is_requeued(db):
    user = make_user(db)
    check = _check(db, user, status=CheckStatus.processing)
    check.claimed_at = utcnow() - timedelta(minutes=settings.worker_stale_minutes + 5)
    check.attempts = 1
    db.commit()

    assert jobq.reclaim_stale(db) == 1
    db.refresh(check)
    assert check.status == CheckStatus.queued
    assert check.claimed_by is None


def test_repeatedly_failing_check_is_stopped_rather_than_looping(db):
    user = make_user(db)
    check = _check(db, user, status=CheckStatus.processing)
    check.claimed_at = utcnow() - timedelta(minutes=settings.worker_stale_minutes + 5)
    check.attempts = jobq.MAX_ATTEMPTS
    db.commit()

    jobq.reclaim_stale(db)
    db.refresh(check)
    assert check.status == CheckStatus.failed
    assert "interrupted" in (check.error or "")


def test_fresh_processing_check_is_left_alone(db):
    user = make_user(db)
    check = _check(db, user, status=CheckStatus.processing)
    check.claimed_at = utcnow()
    db.commit()
    assert jobq.reclaim_stale(db) == 0


def test_depth_reports_queue_state(db):
    user = make_user(db)
    _check(db, user)
    _check(db, user, status=CheckStatus.processing)
    state = jobq.depth(db)
    assert state["queued"] == 1 and state["processing"] == 1
    assert state["oldest_pending_seconds"] is not None


# --------------------------------------------------------------------------
# rate limiting
# --------------------------------------------------------------------------


class _Req:
    def __init__(self, ip="1.2.3.4", headers=None):
        self.headers = headers or {}
        self.client = type("C", (), {"host": ip})()


@pytest.fixture(autouse=True)
def _clear_limits():
    ratelimit.reset()
    yield
    ratelimit.reset()


def test_per_ip_burst_limit_trips(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_checks_per_hour_ip", 3)
    monkeypatch.setattr(settings, "rate_limit_checks_per_day", 1000)
    req = _Req()
    for i in range(3):
        ratelimit.limit_check_run(req, f"user-{i}")
    with pytest.raises(Exception) as exc:
        ratelimit.limit_check_run(req, "user-x")
    assert exc.value.status_code == 429


def test_per_account_daily_limit_trips(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_checks_per_day", 2)
    monkeypatch.setattr(settings, "rate_limit_checks_per_hour_ip", 1000)
    for i in range(2):
        ratelimit.limit_check_run(_Req(ip=f"9.9.9.{i}"), "same-user")
    with pytest.raises(Exception) as exc:
        ratelimit.limit_check_run(_Req(ip="9.9.9.9"), "same-user")
    assert exc.value.status_code == 429


def test_different_ips_have_separate_budgets(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_checks_per_hour_ip", 1)
    monkeypatch.setattr(settings, "rate_limit_checks_per_day", 1000)
    ratelimit.limit_check_run(_Req(ip="1.1.1.1"), "a")
    ratelimit.limit_check_run(_Req(ip="2.2.2.2"), "b")  # must not raise


def test_limits_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_checks_per_hour_ip", 1)
    for _ in range(10):
        ratelimit.limit_check_run(_Req(), "user")


def test_client_ip_honours_forwarded_header():
    req = _Req(ip="10.0.0.1", headers={"x-forwarded-for": "203.0.113.9, 10.0.0.1"})
    assert ratelimit.client_ip(req) == "203.0.113.9"


def test_remaining_today_counts_down(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_checks_per_day", 5)
    monkeypatch.setattr(settings, "rate_limit_checks_per_hour_ip", 1000)
    assert ratelimit.remaining_today("u") == 5
    ratelimit.limit_check_run(_Req(), "u")
    assert ratelimit.remaining_today("u") == 4
