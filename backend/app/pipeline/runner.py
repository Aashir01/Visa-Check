"""End-to-end check execution.

    upload → OCR → classify → extract → rules → LLM review → score → persist

Ordering is chosen so the expensive steps run last and only on what survives:
classification narrows what to extract, deterministic extraction narrows what
to ask the model, and the model is skipped entirely once the budget is spent.
A check never fails because the LLM was unavailable — it degrades to
deterministic findings and says so in the report.
"""

from __future__ import annotations

import logging
import time
from datetime import date

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Check, CheckStatus, CostEvent, Document, ReviewItem, utcnow
from .. import storage
from . import classify as classify_mod
from . import extract as extract_mod
from . import ocr as ocr_mod
from . import photo as photo_mod
from . import qualitative
from .doctypes import label_for
from .llm import LlmClient, LlmUsage
from .normalize import parse_date
from .rules_engine import CheckContext, DocView, RulesEngine
from .scoring import build_summary, overall_confidence, score_check
from .timeline import build_timeline

log = logging.getLogger(__name__)

_IMAGE_SUFFIX = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
                 "image/webp": ".webp", "application/pdf": ".pdf"}


def run_check(db: Session, check: Check, pack: dict) -> Check:
    started = time.monotonic()
    check.status = CheckStatus.processing
    check.error = None
    db.commit()

    usage = LlmUsage()
    # The free tier runs deterministic checks only (§2), which is what keeps a
    # free check's marginal cost at zero. A disabled client makes every LLM
    # call a no-op rather than requiring each caller to remember the rule.
    llm = LlmClient(usage=usage, enabled=bool(check.ai_enabled))

    try:
        documents = (
            db.query(Document).filter(Document.check_id == check.id).all()
        )
        if not documents:
            raise ValueError("No documents were uploaded for this check.")

        views = _ingest(db, documents, pack, llm)

        ctx = CheckContext(
            pack=pack,
            profile=check.applicant_profile or "employed",
            documents=views,
            travel_start=parse_date(check.travel_from),
            travel_end=parse_date(check.travel_to),
            # Evaluate against the appointment date when the applicant gave one.
            # A statement that is fine today can be out of date by an
            # appointment three weeks away, and that later date is the one the
            # consulate actually applies.
            submission_date=parse_date(check.submission_date) or date.today(),
            destination_country=(check.applicant_meta or {}).get("destination_country"),
        )

        engine = RulesEngine(pack)
        issues, passed, skipped = engine.evaluate(ctx)

        llm_issues, llm_passed = qualitative.review(llm, pack, views)
        issues.extend(llm_issues)
        passed.extend(llm_passed)

        from .rules_engine import SEVERITY_ORDER

        issues.sort(
            key=lambda i: (
                SEVERITY_ORDER.get(i["severity"], 3),
                -float(i.get("confidence", 0.5)),
            )
        )

        scoring = score_check(issues, pack.get("severity_weights"))
        has_ai_criteria = bool((pack.get("llm_review") or {}).get("criteria"))
        if not has_ai_criteria:
            ai_status = "not_applicable"
        elif not check.ai_enabled:
            ai_status = "not_in_tier"
        elif llm.usage.exhausted():
            ai_status = "budget_exhausted"
        elif not llm.configured:
            ai_status = "unavailable"
        else:
            ai_status = "included"
        degraded = ai_status in ("not_in_tier", "budget_exhausted", "unavailable")

        check.risk_score = scoring["score"]
        check.risk_band = scoring["band"]
        check.issues = issues
        check.summary = build_summary(
            scoring, issues, passed, pack, skipped=skipped, ai_status=ai_status
        )
        check.confidence = overall_confidence(views, issues)
        check.extraction = {
            "scoring": scoring,
            "passed": passed,
            "skipped": skipped,
            "degraded_llm": degraded,
            "ai_status": ai_status,
            "llm_provider": llm.provider,
            "llm_model": llm.model,
            "tier": check.tier,
            "trip_days": ctx.trip_days,
            "submission_date": ctx.submission_date.isoformat(),
            "submission_date_source": (
                "appointment" if check.submission_date else "today"
            ),
            "timeline": build_timeline(ctx, pack),
            "travel_start": ctx.effective_travel_start.isoformat()
            if ctx.effective_travel_start else None,
            "travel_end": ctx.effective_travel_end.isoformat()
            if ctx.effective_travel_end else None,
            "documents": [
                {
                    "id": v.id,
                    "type": v.doc_type,
                    "label": label_for(v.doc_type),
                    "filename": v.filename,
                    "confidence": v.confidence,
                    "fields": {k: val for k, val in v.fields.items()
                               if not k.startswith("_")},
                }
                for v in views
            ],
        }

        check.llm_cost_usd = usage.usd
        check.tokens_in = usage.tokens_in
        check.tokens_out = usage.tokens_out
        check.status = CheckStatus.complete
        check.completed_at = utcnow()

    except Exception as exc:  # noqa: BLE001 - surface failure, never crash the worker
        log.exception("check %s failed", check.id)
        check.status = CheckStatus.failed
        check.error = str(exc)[:900]

    check.duration_ms = int((time.monotonic() - started) * 1000)
    _record_costs(db, check, usage)
    db.commit()

    if check.status == CheckStatus.complete:
        _maybe_queue_review(db, check)
    return check


# --------------------------------------------------------------------------


def _ingest(db: Session, documents: list[Document], pack: dict, llm) -> list[DocView]:
    """OCR, classify and extract every uploaded file."""
    provider_name = (pack.get("ocr") or {}).get("provider") or settings.ocr_provider
    provider = ocr_mod.get_provider(provider_name)

    texts: dict[str, str] = {}
    pending_classification: list[dict] = []

    for doc in documents:
        text = ""
        if doc.storage_path:
            suffix = _IMAGE_SUFFIX.get((doc.mime or "").lower(), "")
            try:
                with storage.materialise(doc.storage_path, suffix=suffix) as path:
                    result = provider.extract(path, doc.mime)
                    text = result.text
                    doc.ocr_engine = result.engine
                    doc.ocr_confidence = round(result.confidence, 3)
                    doc.page_count = result.page_count

                    if _is_image(doc.mime):
                        doc.image_metrics = photo_mod.analyse(path).as_dict()
            except Exception as exc:  # noqa: BLE001
                log.warning("ingest failed for %s: %s", doc.filename, exc)
                doc.ocr_engine = "failed"
                doc.ocr_confidence = 0.0

        texts[doc.id] = text
        doc.text_excerpt = text[:4000] if text else None

        # --- classify ---
        if doc.doc_type_override:
            doc.doc_type = doc.doc_type_override
            doc.doc_type_confidence = 1.0
            doc.doc_type_source = "user"
        else:
            c = classify_mod.classify_text(text)
            if classify_mod.needs_llm(c) and _is_image(doc.mime) and len(text.strip()) < 60:
                c = classify_mod.classify_image_without_text(doc.image_metrics)
            doc.doc_type = c.doc_type
            doc.doc_type_confidence = c.confidence
            doc.doc_type_source = c.source
            if classify_mod.needs_llm(c) and text.strip():
                pending_classification.append(
                    {"id": doc.id, "filename": doc.filename, "text": text}
                )

    # One batched call for everything the keyword pass could not settle.
    if pending_classification:
        resolved = classify_mod.classify_batch_with_llm(llm, pending_classification)
        for doc in documents:
            c = resolved.get(doc.id)
            if c and not doc.doc_type_override:
                doc.doc_type = c.doc_type
                doc.doc_type_confidence = c.confidence
                doc.doc_type_source = c.source

    # --- deterministic extraction ---
    extractions: dict[str, extract_mod.Extraction] = {}
    gaps: list[dict] = []
    for doc in documents:
        dtype = doc.effective_type or "unknown"
        ex = extract_mod.extract_document(dtype, texts.get(doc.id, ""))
        extractions[doc.id] = ex

        wanted = extract_mod.WANTED.get(dtype, [])
        missing = ex.missing(wanted)
        if missing and texts.get(doc.id):
            gaps.append(
                {"id": doc.id, "type": dtype, "text": texts[doc.id], "missing": missing}
            )

    # --- one batched LLM call to fill what regex could not ---
    if gaps:
        filled = extract_mod.llm_fill_gaps(llm, gaps)
        for doc_id, payload in filled.items():
            ex = extractions.get(doc_id)
            if not ex:
                continue
            for key, value in (payload.get("fields") or {}).items():
                ex.set(key, value, "llm")  # never overwrites a deterministic value
            ex.confidence = max(ex.confidence, float(payload.get("confidence", 0.6)) * 0.9)

    views: list[DocView] = []
    for doc in documents:
        ex = extractions[doc.id]
        doc.extracted = {"fields": ex.fields, "sources": ex.sources, "notes": ex.notes}
        combined = _combined_confidence(doc, ex)
        views.append(
            DocView(
                id=doc.id,
                doc_type=doc.effective_type or "unknown",
                filename=doc.filename,
                fields=dict(ex.fields),
                metrics=doc.image_metrics or {},
                confidence=combined,
                text=texts.get(doc.id, ""),
            )
        )
    db.commit()
    return views


def _combined_confidence(doc: Document, ex) -> float:
    """How much we trust our reading of this one document."""
    parts = [
        float(doc.doc_type_confidence or 0),
        float(doc.ocr_confidence or 0),
        float(ex.confidence or 0),
    ]
    weights = [0.4, 0.3, 0.3]
    return round(sum(p * w for p, w in zip(parts, weights, strict=True)), 3)


def _is_image(mime: str | None) -> bool:
    return (mime or "").lower() in ocr_mod.IMAGE_MIMES


def _record_costs(db: Session, check: Check, usage: LlmUsage) -> None:
    for call in usage.calls:
        if not call.ok or (call.tokens_in == 0 and call.tokens_out == 0):
            continue
        db.add(
            CostEvent(
                check_id=check.id,
                corridor_id=check.corridor_id,
                kind=call.kind,
                model=call.model,
                tokens_in=call.tokens_in,
                tokens_out=call.tokens_out,
                usd=call.usd,
            )
        )


def _maybe_queue_review(db: Session, check: Check) -> None:
    """Route uncertain checks to /admin/reviews so corrections become data (§4)."""
    reasons = []
    if (check.confidence or 1.0) < settings.low_confidence_threshold:
        reasons.append(f"overall confidence {check.confidence:.2f}")

    docs = db.query(Document).filter(Document.check_id == check.id).all()
    unknown = [d for d in docs if (d.effective_type or "unknown") == "unknown"]
    if unknown:
        reasons.append(f"{len(unknown)} unclassified document(s)")

    weak = [
        d for d in docs
        if (d.doc_type_confidence or 1.0) < settings.low_confidence_threshold
        and d.doc_type_source != "user"
    ]
    if weak:
        reasons.append(f"{len(weak)} low-confidence classification(s)")

    failed_ocr = [d for d in docs if (d.ocr_confidence or 1.0) < 0.35]
    if failed_ocr:
        reasons.append(f"{len(failed_ocr)} document(s) with poor OCR")

    if not reasons:
        return

    exists = (
        db.query(ReviewItem)
        .filter(ReviewItem.check_id == check.id, ReviewItem.status == "open")
        .first()
    )
    if exists:
        return

    db.add(
        ReviewItem(
            check_id=check.id,
            corridor_id=check.corridor_id,
            reason="; ".join(reasons),
            confidence=check.confidence,
            payload={
                "documents": [
                    {
                        "id": d.id,
                        "filename": d.filename,
                        "detected_type": d.effective_type,
                        "type_confidence": d.doc_type_confidence,
                        "ocr_confidence": d.ocr_confidence,
                        "ocr_engine": d.ocr_engine,
                    }
                    for d in docs
                ]
            },
        )
    )
    db.commit()
