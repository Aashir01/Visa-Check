"""A database-backed job queue for check execution.

Deliberately not Redis or Celery. The app already owns a transactional
database, checks are low-frequency and long-running, and adding a broker means
another service to deploy, monitor and pay for. A claim-by-update against the
existing ``checks`` table gives at-least-once delivery with no new
infrastructure.

Two modes, set by ``WORKER_MODE``:

* ``inline`` — the API runs the check in a background task. Fine for
  development and low volume.
* ``queue``  — the API only enqueues; ``python worker.py`` does the work. This
  is what stops a traffic spike from saturating the web process, because OCR
  is CPU-bound and will otherwise starve request handling.
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from .config import settings
from .models import Check, CheckStatus, RulePack, as_utc, utcnow

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def enqueue(db: Session, check: Check) -> None:
    check.status = CheckStatus.queued
    check.error = None
    check.claimed_at = None
    check.claimed_by = None
    db.commit()


def reclaim_stale(db: Session) -> int:
    """Return checks abandoned by a dead worker to the queue."""
    cutoff = utcnow() - timedelta(minutes=settings.worker_stale_minutes)
    stale = (
        db.query(Check)
        .filter(Check.status == CheckStatus.processing, Check.claimed_at < cutoff)
        .all()
    )
    for check in stale:
        if check.attempts >= MAX_ATTEMPTS:
            check.status = CheckStatus.failed
            check.error = (
                "This check was interrupted repeatedly and has been stopped. "
                "Please try running it again."
            )
            log.warning("check %s exceeded %d attempts", check.id, MAX_ATTEMPTS)
        else:
            check.status = CheckStatus.queued
            check.claimed_at = None
            check.claimed_by = None
            log.info("requeued stale check %s", check.id)
    if stale:
        db.commit()
    return len(stale)


def claim_next(db: Session, who: str | None = None) -> Check | None:
    """Atomically take one queued check.

    The UPDATE ... WHERE status='queued' is the lock: whichever worker's
    update reports a row modified owns the job. That is portable across
    SQLite and Postgres without needing SKIP LOCKED.
    """
    who = who or worker_id()

    candidate = (
        db.query(Check)
        .filter(Check.status == CheckStatus.queued)
        .order_by(Check.created_at.asc())
        .first()
    )
    if candidate is None:
        return None

    now = utcnow()
    claimed = (
        db.query(Check)
        .filter(Check.id == candidate.id, Check.status == CheckStatus.queued)
        .update(
            {
                Check.status: CheckStatus.processing,
                Check.claimed_at: now,
                Check.claimed_by: who,
                Check.attempts: Check.attempts + 1,
            },
            synchronize_session=False,
        )
    )
    db.commit()
    if not claimed:
        return None  # another worker won the race

    db.expire_all()
    return db.get(Check, candidate.id)


def execute(db: Session, check: Check) -> Check:
    """Run one claimed check to completion."""
    from .pipeline.runner import run_check

    pack = db.get(RulePack, check.rulepack_id) if check.rulepack_id else None
    if not pack:
        check.status = CheckStatus.failed
        check.error = "The rule pack for this check no longer exists."
        db.commit()
        return check

    return run_check(db, check, pack.data or {})


def depth(db: Session) -> dict:
    """Queue health, for /admin and /health."""
    queued = db.query(Check).filter(Check.status == CheckStatus.queued).count()
    processing = db.query(Check).filter(Check.status == CheckStatus.processing).count()
    oldest = (
        db.query(Check)
        .filter(or_(Check.status == CheckStatus.queued,
                    Check.status == CheckStatus.processing))
        .order_by(Check.created_at.asc())
        .first()
    )
    age = None
    if oldest:
        age = int((utcnow() - as_utc(oldest.created_at)).total_seconds())
    return {
        "queued": queued,
        "processing": processing,
        "oldest_pending_seconds": age,
        "worker_mode": settings.worker_mode,
    }
