"""Check lifecycle: create → upload → run → report."""

from __future__ import annotations

import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal, get_db
from ..deps import active_pack, current_user, owned_check
from ..models import (
    Check,
    CheckStatus,
    Corridor,
    Document,
    Role,
    RulePack,
    User,
    utcnow,
)
from ..pipeline.doctypes import DOC_TYPES, label_for
from ..pipeline.runner import run_check
from ..report.pdf import build_report_pdf
from ..schemas import (
    CheckCreate,
    CheckOut,
    CheckSummaryOut,
    DocumentOut,
    DocumentTypeOverride,
)
from .. import storage

log = logging.getLogger(__name__)
router = APIRouter(prefix="/checks", tags=["checks"])

ALLOWED_MIMES = {
    "application/pdf",
    "image/jpeg", "image/jpg", "image/png", "image/webp",
}


# --------------------------------------------------------------------------
# serialisation
# --------------------------------------------------------------------------


def _doc_out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id,
        filename=d.filename,
        mime=d.mime,
        size_bytes=d.size_bytes,
        doc_type=d.effective_type,
        doc_type_label=label_for(d.effective_type),
        doc_type_confidence=d.doc_type_confidence,
        doc_type_source=d.doc_type_source,
        ocr_engine=d.ocr_engine,
        ocr_confidence=d.ocr_confidence,
        page_count=d.page_count,
        extracted=d.extracted,
        image_metrics=d.image_metrics,
    )


def _check_out(db: Session, check: Check) -> CheckOut:
    corridor = db.get(Corridor, check.corridor_id)
    pack_meta = None
    if check.rulepack_id:
        pack = db.get(RulePack, check.rulepack_id)
        if pack:
            data = pack.data or {}
            pack_meta = {
                "title": data.get("title"),
                "version": pack.version,
                "effective_date": data.get("effective_date"),
                "disclaimer": data.get("disclaimer"),
                "unverified": pack.unverified,
                "source_notes": data.get("source_notes"),
            }

    return CheckOut(
        id=check.id,
        corridor_id=check.corridor_id,
        corridor_label=corridor.label if corridor else None,
        applicant_profile=check.applicant_profile,
        travel_from=check.travel_from,
        travel_to=check.travel_to,
        status=check.status.value,
        error=check.error,
        risk_score=check.risk_score,
        risk_band=check.risk_band,
        summary=check.summary,
        confidence=check.confidence,
        issues=check.issues,
        extraction=check.extraction,
        rulepack_version=check.rulepack_version,
        rulepack_unverified=check.rulepack_unverified,
        documents=[_doc_out(d) for d in check.documents],
        documents_purged_at=check.documents_purged_at,
        pack_meta=pack_meta,
        created_at=check.created_at,
        completed_at=check.completed_at,
    )


# --------------------------------------------------------------------------
# credits
# --------------------------------------------------------------------------


def _spend_credit(db: Session, user: User) -> bool:
    """Deduct one credit. Personal credits first, then the org pool."""
    if user.role == Role.admin:
        return True
    if user.credits > 0:
        user.credits -= 1
        db.commit()
        return True
    if user.org and user.org.credits > 0:
        user.org.credits -= 1
        db.commit()
        return True
    return False


def _refund_credit(db: Session, user: User) -> None:
    if user.role == Role.admin:
        return
    user.credits += 1
    db.commit()


# --------------------------------------------------------------------------
# endpoints
# --------------------------------------------------------------------------


@router.get("/document-types")
def document_types():
    """Used by the upload UI to offer a manual type override."""
    return [{"key": k, "label": v} for k, v in DOC_TYPES.items()]


@router.post("", response_model=CheckOut, status_code=201)
def create_check(
    payload: CheckCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    corridor = db.get(Corridor, payload.corridor_id)
    if not corridor or not corridor.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Corridor not available")

    pack_row, pack = active_pack(db, corridor)

    profiles = pack.get("profiles") or {}
    if profiles and payload.applicant_profile not in profiles:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Profile '{payload.applicant_profile}' is not offered for this corridor.",
        )

    check = Check(
        user_id=user.id,
        org_id=user.org_id,
        corridor_id=corridor.id,
        rulepack_id=pack_row.id,
        rulepack_version=pack_row.version,
        rulepack_unverified=pack_row.unverified,
        applicant_profile=payload.applicant_profile,
        applicant_meta=payload.applicant_meta,
        travel_from=payload.travel_from,
        travel_to=payload.travel_to,
        status=CheckStatus.draft,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return _check_out(db, check)


@router.post("/{check_id}/documents", response_model=list[DocumentOut], status_code=201)
async def upload_documents(
    check_id: str,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    check = owned_check(check_id, db, user)
    if check.status not in (CheckStatus.draft, CheckStatus.failed):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This check has already been run. Start a new check to analyse different "
            "documents.",
        )

    existing = db.query(Document).filter(Document.check_id == check.id).count()
    if existing + len(files) > settings.max_files_per_check:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"A check accepts at most {settings.max_files_per_check} files.",
        )

    limit = settings.max_upload_mb * 1024 * 1024
    created: list[Document] = []

    for upload in files:
        mime = (upload.content_type or "").lower()
        if mime not in ALLOWED_MIMES:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"{upload.filename}: only PDF, JPG, PNG and WebP files are accepted.",
            )
        raw = await upload.read()
        if not raw:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"{upload.filename} is empty."
            )
        if len(raw) > limit:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"{upload.filename} exceeds the {settings.max_upload_mb} MB limit.",
            )

        doc = Document(
            check_id=check.id,
            filename=(upload.filename or "document")[:400],
            mime=mime,
            size_bytes=len(raw),
        )
        db.add(doc)
        db.flush()  # need doc.id for the storage path

        path, digest = storage.save_document(check.id, doc.id, raw)
        doc.storage_path = path
        doc.sha256 = digest
        created.append(doc)

    db.commit()
    for d in created:
        db.refresh(d)
    return [_doc_out(d) for d in created]


@router.patch("/{check_id}/documents/{document_id}", response_model=DocumentOut)
def override_document_type(
    check_id: str,
    document_id: str,
    payload: DocumentTypeOverride,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Let the user correct a misclassification before running the check."""
    check = owned_check(check_id, db, user)
    doc = db.get(Document, document_id)
    if not doc or doc.check_id != check.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    if payload.doc_type not in DOC_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown document type")

    doc.doc_type_override = payload.doc_type
    doc.doc_type = payload.doc_type
    doc.doc_type_confidence = 1.0
    doc.doc_type_source = "user"
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@router.delete("/{check_id}/documents/{document_id}", status_code=204)
def delete_document(
    check_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    check = owned_check(check_id, db, user)
    if check.status not in (CheckStatus.draft, CheckStatus.failed):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Documents cannot be removed after the run."
        )
    doc = db.get(Document, document_id)
    if not doc or doc.check_id != check.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    db.delete(doc)
    db.commit()
    return Response(status_code=204)


def _execute(check_id: str) -> None:
    """Background worker body. Owns its own session."""
    db = SessionLocal()
    try:
        check = db.get(Check, check_id)
        if not check:
            return
        pack = db.get(RulePack, check.rulepack_id)
        if not pack:
            check.status = CheckStatus.failed
            check.error = "The rule pack for this check no longer exists."
            db.commit()
            return
        run_check(db, check, pack.data or {})
    except Exception:  # noqa: BLE001
        log.exception("background run failed for check %s", check_id)
    finally:
        db.close()


@router.post("/{check_id}/run", response_model=CheckOut)
def run(
    check_id: str,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    check = owned_check(check_id, db, user)
    if check.status in (CheckStatus.queued, CheckStatus.processing):
        return _check_out(db, check)
    if check.status == CheckStatus.complete:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This check has already completed. Create a new check to re-run.",
        )
    if not db.query(Document).filter(Document.check_id == check.id).count():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Upload at least one document first."
        )

    # A previously failed check already consumed its credit.
    if check.status != CheckStatus.failed and not _spend_credit(db, user):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "You have no checks remaining. Add credits from your account page.",
        )

    check.status = CheckStatus.queued
    check.error = None
    db.commit()

    background.add_task(_execute, check.id)
    db.refresh(check)
    return _check_out(db, check)


@router.get("", response_model=list[CheckSummaryOut])
def list_checks(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    q = db.query(Check)
    if user.role == Role.admin:
        pass
    elif user.org_id:
        q = q.filter(Check.org_id == user.org_id)
    else:
        q = q.filter(Check.user_id == user.id)

    rows = (
        q.order_by(Check.created_at.desc()).offset(offset).limit(limit).all()
    )
    corridors = {c.id: c for c in db.query(Corridor).all()}

    out = []
    for check in rows:
        issues = check.issues or []
        out.append(
            CheckSummaryOut(
                id=check.id,
                corridor_id=check.corridor_id,
                corridor_label=corridors[check.corridor_id].label
                if check.corridor_id in corridors else None,
                applicant_profile=check.applicant_profile,
                status=check.status.value,
                risk_score=check.risk_score,
                risk_band=check.risk_band,
                document_count=len(check.documents),
                critical_count=sum(1 for i in issues if i.get("severity") == "critical"),
                warning_count=sum(1 for i in issues if i.get("severity") == "warning"),
                info_count=sum(1 for i in issues if i.get("severity") == "info"),
                rulepack_version=check.rulepack_version,
                created_at=check.created_at,
                completed_at=check.completed_at,
            )
        )
    return out


@router.get("/{check_id}", response_model=CheckOut)
def get_check(
    check_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return _check_out(db, owned_check(check_id, db, user))


@router.get("/{check_id}/report.pdf")
def download_report(
    check_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    check = owned_check(check_id, db, user)
    if check.status != CheckStatus.complete:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The report is not ready yet."
        )

    corridor = db.get(Corridor, check.corridor_id)
    pack = db.get(RulePack, check.rulepack_id)
    if not (corridor and pack):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "The checklist for this report is unavailable."
        )

    brand = {}
    if user.org:
        brand = {
            "name": user.org.brand_name or user.org.name,
            "color": user.org.brand_color,
        }

    pdf = build_report_pdf(
        check=check,
        corridor=corridor,
        pack=pack.data or {},
        documents=list(check.documents),
        brand=brand,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="visaguard-report-{check.id[:8]}.pdf"'
        },
    )


@router.delete("/{check_id}", status_code=204)
def delete_check(
    check_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    check = owned_check(check_id, db, user)
    storage.purge_check(check.id)
    db.delete(check)
    db.commit()
    return Response(status_code=204)
