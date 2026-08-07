#!/usr/bin/env python3
"""Background worker for running checks.

OCR is CPU-bound and a check can take tens of seconds. Running that inside the
web process means a burst of uploads starves request handling, so in
production the API only enqueues and this does the work:

    WORKER_MODE=queue python -m uvicorn app.main:app   # API
    WORKER_MODE=queue python worker.py --concurrency 4  # worker(s)

Safe to run several instances — jobs are claimed atomically, and a job
abandoned by a crashed worker is returned to the queue after
``WORKER_STALE_MINUTES``.
"""

from __future__ import annotations

import argparse
import logging
import signal
import threading
import time

from app.config import settings
from app.db import SessionLocal, init_db
from app import queue as jobq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [worker] %(message)s",
)
log = logging.getLogger("worker")

_stop = threading.Event()


def _shutdown(signum, _frame):
    log.info("signal %s received; finishing current check then exiting", signum)
    _stop.set()


def _loop(slot: int, poll: float) -> None:
    who = f"{jobq.worker_id()}#{slot}"
    while not _stop.is_set():
        db = SessionLocal()
        try:
            check = jobq.claim_next(db, who)
            if check is None:
                _stop.wait(poll)
                continue

            log.info("running check %s (attempt %d)", check.id, check.attempts)
            started = time.monotonic()
            result = jobq.execute(db, check)
            log.info(
                "check %s -> %s in %.1fs (score=%s, cost=$%.4f)",
                result.id,
                result.status.value,
                time.monotonic() - started,
                result.risk_score,
                result.llm_cost_usd or 0.0,
            )
        except Exception:  # noqa: BLE001 - a worker must never die on one job
            log.exception("worker slot %d failed on a job", slot)
            _stop.wait(poll)
        finally:
            db.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="VisaGuard check worker.")
    ap.add_argument("--concurrency", type=int, default=settings.worker_concurrency)
    ap.add_argument("--poll", type=float, default=settings.worker_poll_seconds)
    ap.add_argument(
        "--once", action="store_true",
        help="Drain the queue and exit, instead of polling forever.",
    )
    args = ap.parse_args()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()

    db = SessionLocal()
    try:
        reclaimed = jobq.reclaim_stale(db)
        if reclaimed:
            log.info("requeued %d stale check(s)", reclaimed)
        if args.once:
            drained = 0
            while True:
                check = jobq.claim_next(db)
                if check is None:
                    break
                jobq.execute(db, check)
                drained += 1
            log.info("drained %d check(s)", drained)
            return 0
    finally:
        db.close()

    log.info(
        "starting %d worker slot(s), polling every %.1fs",
        args.concurrency, args.poll,
    )
    threads = [
        threading.Thread(target=_loop, args=(i, args.poll), daemon=True)
        for i in range(max(1, args.concurrency))
    ]
    for t in threads:
        t.start()

    # Periodically rescue jobs stranded by a worker that died mid-check.
    while not _stop.is_set():
        _stop.wait(60)
        if _stop.is_set():
            break
        db = SessionLocal()
        try:
            jobq.reclaim_stale(db)
        except Exception:  # noqa: BLE001
            log.exception("stale reclaim failed")
        finally:
            db.close()

    for t in threads:
        t.join(timeout=30)
    log.info("worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
