"""Tests for the 30-day retention promise.

The footer of every page and the README both say uploaded documents are
deleted automatically after 30 days, without qualification. That is a promise
about every file a user hands us, and it is the kind of promise that rots
quietly: a new model that stores blobs is easy to add and easy to forget to
purge. Refusal letters were exactly that — stored from the day the feature
landed, and covered by nothing.

So these tests are less about the purge algorithm than about the claim. If a
future record type holds uploads, the shape here is what it has to satisfy.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import storage
from app.config import settings
from app.db import Base
from app.models import Check, CheckStatus, Document, Refusal, utcnow


@pytest.fixture
def db(tmp_path, monkeypatch):
    # Point blob storage at the tmp dir, so a failing test cannot delete
    # anything real and cannot see another run's files.
    monkeypatch.setattr(storage, "STORAGE_ROOT", tmp_path / "blobs")
    engine = create_engine(
        f"sqlite:///{tmp_path/'r.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def _aged(days: int):
    return utcnow() - timedelta(days=days)


def _check_with_file(db, *, age_days: int) -> Check:
    row = Check(
        user_id="u1",
        corridor_id="c1",
        rulepack_id="rp1",
        applicant_profile="employed",
        status=CheckStatus.complete,
        created_at=_aged(age_days),
    )
    db.add(row)
    db.flush()
    path, _ = storage.save_document(row.id, "d1", b"passport bytes")
    db.add(Document(
        check_id=row.id, filename="passport.pdf", mime="application/pdf",
        size_bytes=14, storage_path=path, sha256="x",
    ))
    db.commit()
    return row


def _refusal_with_file(db, *, age_days: int) -> Refusal:
    row = Refusal(user_id="u1", status="decoded", ground_codes=["no_insurance"],
                  created_at=_aged(age_days))
    db.add(row)
    db.flush()
    path, _ = storage.save_document(row.id, row.id, b"refusal letter bytes")
    row.storage_path = path
    row.text_excerpt = "AHMED RAZA KHAN, born 1990-01-01, refused on ground 7"
    db.commit()
    return row


def _files_under(root, record_id) -> int:
    d = root / record_id
    return sum(1 for _ in d.glob("*")) if d.exists() else 0


# --------------------------------------------------------------------------


def test_old_check_documents_are_deleted(db, tmp_path):
    check = _check_with_file(db, age_days=settings.retention_days + 1)
    assert _files_under(storage.STORAGE_ROOT, check.id) == 1

    result = storage.purge_expired(db)

    assert result["checks_purged"] == 1
    assert _files_under(storage.STORAGE_ROOT, check.id) == 0
    assert db.get(Document, db.query(Document).one().id).storage_path is None


def test_old_refusal_letters_are_deleted_too(db):
    """The promise does not say "documents attached to a check"."""
    refusal = _refusal_with_file(db, age_days=settings.retention_days + 1)
    assert _files_under(storage.STORAGE_ROOT, refusal.id) == 1

    result = storage.purge_expired(db)

    assert result["refusals_purged"] == 1
    assert _files_under(storage.STORAGE_ROOT, refusal.id) == 0
    assert db.get(Refusal, refusal.id).storage_path is None


def test_the_raw_letter_text_goes_with_the_file(db):
    """An excerpt naming the applicant is the document, in a different column.

    Deleting the blob and keeping the text would satisfy the letter of the
    promise and none of its point.
    """
    refusal = _refusal_with_file(db, age_days=settings.retention_days + 1)
    storage.purge_expired(db)
    assert db.get(Refusal, refusal.id).text_excerpt is None


def test_the_decoded_grounds_survive_the_purge(db):
    """What we learn from a refusal is not personal data and must outlive it —
    otherwise the rule packs lose their only real feedback."""
    refusal = _refusal_with_file(db, age_days=settings.retention_days + 1)
    storage.purge_expired(db)
    row = db.get(Refusal, refusal.id)
    assert row.ground_codes == ["no_insurance"]
    assert row.status == "decoded"


def test_recent_records_are_left_alone(db):
    check = _check_with_file(db, age_days=1)
    refusal = _refusal_with_file(db, age_days=1)

    result = storage.purge_expired(db)

    assert result == {"checks_purged": 0, "refusals_purged": 0, "files_removed": 0}
    assert _files_under(storage.STORAGE_ROOT, check.id) == 1
    assert _files_under(storage.STORAGE_ROOT, refusal.id) == 1
    assert db.get(Refusal, refusal.id).text_excerpt is not None


def test_purge_is_idempotent(db):
    """A daily cron runs this repeatedly; the second run must be a no-op rather
    than re-reporting the same records."""
    _check_with_file(db, age_days=settings.retention_days + 1)
    _refusal_with_file(db, age_days=settings.retention_days + 1)

    first = storage.purge_expired(db)
    second = storage.purge_expired(db)

    assert first["files_removed"] == 2
    assert second == {"checks_purged": 0, "refusals_purged": 0, "files_removed": 0}


def test_a_record_whose_files_are_already_gone_does_not_break_the_run(db):
    """Disk and database can disagree — a restore, a manual delete. One missing
    directory must not stop the rest of the purge."""
    refusal = _refusal_with_file(db, age_days=settings.retention_days + 1)
    check = _check_with_file(db, age_days=settings.retention_days + 1)
    import shutil

    shutil.rmtree(storage.STORAGE_ROOT / refusal.id)

    result = storage.purge_expired(db)

    assert result["refusals_purged"] == 1
    assert result["checks_purged"] == 1
    assert _files_under(storage.STORAGE_ROOT, check.id) == 0
