"""Encrypted blob storage for uploaded documents.

Files never touch disk in plaintext. Reading one yields a temporary plaintext
copy that the caller is responsible for discarding — the pipeline does this
inside a context manager so the window is measured in milliseconds.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import tempfile
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

from .config import settings
from .security import decrypt_bytes, encrypt_bytes

STORAGE_ROOT = Path(settings.storage_dir)


def _check_dir(check_id: str) -> Path:
    d = STORAGE_ROOT / check_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_document(check_id: str, doc_id: str, raw: bytes) -> tuple[str, str]:
    """Encrypt and persist. Returns (relative_path, sha256_of_plaintext)."""
    digest = hashlib.sha256(raw).hexdigest()
    path = _check_dir(check_id) / f"{doc_id}.enc"
    path.write_bytes(encrypt_bytes(raw))
    os.chmod(path, 0o600)
    return str(path.relative_to(STORAGE_ROOT)), digest


def read_document(relative_path: str) -> bytes:
    return decrypt_bytes((STORAGE_ROOT / relative_path).read_bytes())


@contextlib.contextmanager
def materialise(relative_path: str, suffix: str = "") -> Iterator[Path]:
    """Decrypt to a temp file for tools that need a real path (tesseract)."""
    raw = read_document(relative_path)
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(raw)
        os.chmod(tmp, 0o600)
        yield Path(tmp)
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp)


def purge_check(check_id: str) -> int:
    """Delete every stored blob for a check. Returns files removed."""
    d = STORAGE_ROOT / check_id
    if not d.exists():
        return 0
    n = sum(1 for _ in d.glob("*"))
    shutil.rmtree(d, ignore_errors=True)
    return n


def purge_expired(db) -> dict:
    """Delete blobs past the retention window (§9).

    Two kinds of record hold uploaded files, and both are covered here — the
    footer promises deletion after 30 days without qualification, and a refusal
    letter is if anything the more sensitive of the two: it names the applicant,
    the consulate, and the grounds they were refused on.

    What survives in both cases is the derived record — the report, the decoded
    grounds, the caught/missed grading. Those carry no document contents and are
    what the rule packs learn from. What goes is everything the applicant
    actually uploaded, plus the raw text read out of it.

    Run from the ``purge`` CLI command on a daily cron.
    """
    from .models import Check, Document, Refusal, utcnow

    cutoff = utcnow() - timedelta(days=settings.retention_days)
    files = 0

    stale_checks = (
        db.query(Check)
        .filter(Check.created_at < cutoff, Check.documents_purged_at.is_(None))
        .all()
    )
    for chk in stale_checks:
        files += purge_check(chk.id)
        for doc in db.query(Document).filter(Document.check_id == chk.id).all():
            doc.storage_path = None
        chk.documents_purged_at = utcnow()

    stale_refusals = (
        db.query(Refusal)
        .filter(Refusal.created_at < cutoff, Refusal.documents_purged_at.is_(None))
        .all()
    )
    for ref in stale_refusals:
        files += purge_check(ref.id)
        ref.storage_path = None
        # The excerpt is raw letter text — name, address, case reference. The
        # decoded grounds above it are what we actually needed to keep.
        ref.text_excerpt = None
        ref.documents_purged_at = utcnow()

    db.commit()
    return {
        "checks_purged": len(stale_checks),
        "refusals_purged": len(stale_refusals),
        "files_removed": files,
    }
