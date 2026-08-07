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
    """Delete blobs for checks older than the retention window (§9).

    The Check row and its report survive; only the source documents go. Run
    from the ``purge`` CLI command on a daily cron.
    """
    from .models import Check, Document, utcnow

    cutoff = utcnow() - timedelta(days=settings.retention_days)
    stale = (
        db.query(Check)
        .filter(Check.created_at < cutoff, Check.documents_purged_at.is_(None))
        .all()
    )
    files = 0
    for chk in stale:
        files += purge_check(chk.id)
        for doc in db.query(Document).filter(Document.check_id == chk.id).all():
            doc.storage_path = None
        chk.documents_purged_at = utcnow()
    db.commit()
    return {"checks_purged": len(stale), "files_removed": files}
