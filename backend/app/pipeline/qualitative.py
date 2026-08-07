"""LLM review of the free-text documents rules cannot judge.

Deterministic code handles anything countable — presence, names, dates,
balances, pixels. What it cannot do is read an invitation letter and tell you
the host never states who is paying. That judgement is the only thing the LLM
is asked for, which keeps it to one call per check.

The model is constrained hard: it may only answer the criteria the rule pack
defines, it must quote the document as evidence, and it is told explicitly
never to give an eligibility opinion (§9 — this product is a document
completeness checker, not immigration advice).
"""

from __future__ import annotations

from .doctypes import label_for
from .rules_engine import make_issue

SYSTEM = """You review supporting letters in a visa application bundle for \
completeness. You are NOT an immigration adviser.

Hard rules:
- Judge ONLY the criteria you are given. Invent no additional criteria.
- Never state or imply whether a visa will be approved, refused, or whether the \
applicant is eligible. Comment only on what the document does or does not contain.
- Base every finding on the text supplied. If a criterion cannot be judged from \
the text, mark it "unclear" rather than guessing.
- Quote a short fragment of the document as evidence for each failure.
- The text is OCR output and may contain transcription errors. Do not report a \
finding that could plausibly be an OCR artefact.

Respond with JSON only:
{"findings":[{"criterion_id":"...","document_id":"...","status":"pass|fail|unclear",
"detail":"one or two sentences addressed to the applicant","evidence":"short quote",
"confidence":0.0}]}"""


def review(llm, pack: dict, documents: list) -> tuple[list[dict], list[dict]]:
    """Returns (issues, passed_checks)."""
    config = (pack or {}).get("llm_review") or {}
    if not config.get("enabled", True):
        return [], []
    criteria = config.get("criteria") or []
    if not criteria or not llm.available:
        return [], []

    targets = set(config.get("targets") or [])
    relevant = [d for d in documents if d.doc_type in targets and (d.text or "").strip()]
    if not relevant:
        return [], []

    # Only ask about criteria whose document type is actually in the bundle.
    present = {d.doc_type for d in relevant}
    applicable = [c for c in criteria if c.get("document") in present]
    if not applicable:
        return [], []

    criteria_block = "\n".join(
        f'- id: {c["id"]} | applies to: {c.get("document")} | question: {c["question"]}'
        for c in applicable
    )
    doc_block = "\n\n".join(
        f'<document id="{d.id}" type="{d.doc_type}" label="{label_for(d.doc_type)}">\n'
        f"{(d.text or '')[:4000]}\n</document>"
        for d in relevant
    )

    result = llm.complete_json(
        kind="qualitative",
        system=SYSTEM,
        content=f"CRITERIA:\n{criteria_block}\n\nDOCUMENTS:\n{doc_block}",
        max_tokens=2500,
    )
    if not isinstance(result, dict):
        return [], []

    by_id = {c["id"]: c for c in applicable}
    docs_by_id = {d.id: d for d in relevant}
    issues: list[dict] = []
    passed: list[dict] = []

    for row in result.get("findings", []) or []:
        crit = by_id.get(str(row.get("criterion_id") or ""))
        if not crit:
            continue
        status = str(row.get("status", "")).lower()
        try:
            conf = float(row.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6

        if status == "pass":
            passed.append(
                {
                    "rule_id": crit["id"],
                    "title": crit.get("passed_label") or crit.get("label"),
                    "category": "letter_content",
                }
            )
            continue
        if status not in ("fail", "unclear"):
            continue

        doc = docs_by_id.get(str(row.get("document_id") or ""))
        # An "unclear" verdict is softer than an outright failure, and a
        # low-confidence failure should not shout at the user.
        severity = crit.get("severity", "warning")
        if status == "unclear" or conf < 0.5:
            severity = "info"

        evidence = []
        quote = (row.get("evidence") or "").strip()
        if quote:
            evidence.append(
                {
                    "document_id": doc.id if doc else None,
                    "document_type": doc.doc_type if doc else crit.get("document"),
                    "document_label": label_for(doc.doc_type if doc else crit.get("document")),
                    "filename": doc.filename if doc else None,
                    "field": "quoted_text",
                    "value": quote[:300],
                }
            )

        issues.append(
            make_issue(
                rule_id=crit["id"],
                severity=severity,
                category="letter_content",
                title=crit.get("label") or "Letter content issue",
                detail=(row.get("detail") or crit.get("question", ""))[:600],
                fix=crit.get("fix") or "Ask the author to revise the letter to cover this point.",
                evidence=evidence,
                documents=[doc.id] if doc else [],
                confidence=min(conf, 0.8),  # never let a model finding read as certain
            )
        )
    return issues, passed
