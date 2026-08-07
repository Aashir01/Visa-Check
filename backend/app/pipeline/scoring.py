"""Risk scoring and report summary language.

Scoring is intentionally simple and explainable: every issue carries a
severity weight, weights are summed, and the score is 100 minus that sum.
An agent asked "why is this 62?" can be shown the arithmetic.

Two deliberate choices:

* **Diminishing returns within a severity.** Five missing documents is worse
  than one, but not five times worse — the file is already going to be
  rejected at the counter. Without damping, every incomplete bundle collapses
  to 0 and the score stops discriminating.
* **Confidence-weighted penalties.** A finding the engine is 55% sure about
  moves the score less than one it verified against a passport MRZ.

The wording never says "approved" or "will be accepted" (§9).
"""

from __future__ import annotations

DEFAULT_WEIGHTS = {"critical": 22, "warning": 8, "info": 2}

BANDS = [
    (85, "low", "Low risk",
     "No blocking issues were detected against this checklist. Review the "
     "remaining notes before you submit."),
    (65, "moderate", "Moderate risk",
     "Your bundle is largely complete, but there are issues that commonly "
     "cause delays or requests for more documents."),
    (40, "elevated", "Elevated risk",
     "Several issues were found that are frequently cited in refusals for "
     "this corridor. Fix the critical items before submitting."),
    (0, "high", "High risk",
     "This bundle has significant gaps against the checklist. Submitting as-is "
     "risks losing the visa fee."),
]


def score_check(issues: list[dict], weights: dict | None = None) -> dict:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    counts = {"critical": 0, "warning": 0, "info": 0}
    penalty_by_severity = {"critical": 0.0, "warning": 0.0, "info": 0.0}

    for severity in ("critical", "warning", "info"):
        group = [i for i in issues if i.get("severity") == severity]
        counts[severity] = len(group)
        base = float(w.get(severity, DEFAULT_WEIGHTS.get(severity, 5)))
        total = 0.0
        for rank, issue in enumerate(
            sorted(group, key=lambda i: -float(i.get("confidence", 0.9)))
        ):
            confidence = max(0.3, min(1.0, float(issue.get("confidence", 0.9))))
            # 1st full weight, 2nd 70%, 3rd 49% ... within each severity.
            damping = 0.7**rank
            total += base * confidence * damping
        penalty_by_severity[severity] = round(total, 2)

    penalty = sum(penalty_by_severity.values())
    score = int(round(max(0.0, min(100.0, 100.0 - penalty))))

    # A bundle with any critical finding must not read as "low risk", however
    # few issues it has — a missing passport is not a minor blemish.
    if counts["critical"] and score > 64:
        score = 64
    if counts["critical"] >= 3 and score > 39:
        score = 39

    band_key, band_label, band_message = "high", "High risk", BANDS[-1][3]
    for threshold, key, label, message in BANDS:
        if score >= threshold:
            band_key, band_label, band_message = key, label, message
            break

    return {
        "score": score,
        "band": band_key,
        "band_label": band_label,
        "band_message": band_message,
        "counts": counts,
        "penalty": round(penalty, 2),
        "penalty_by_severity": penalty_by_severity,
    }


def build_summary(
    scoring: dict,
    issues: list[dict],
    passed: list[dict],
    pack: dict,
    *,
    degraded: bool = False,
    skipped: list[dict] | None = None,
) -> str:
    counts = scoring["counts"]
    version = pack.get("version", "unknown")
    title = pack.get("title", "this corridor")

    parts = [
        f"Checked against {title}, checklist version {version}. "
        f"{len(passed)} requirement(s) verified."
    ]

    if not issues:
        parts.append(
            "No issues were detected against this checklist. That is not a "
            "prediction of approval — it means nothing on the checklist is "
            "missing or inconsistent in the documents you uploaded."
        )
    else:
        found = []
        for severity, word in (("critical", "critical"), ("warning", "warning"),
                               ("info", "informational")):
            if counts[severity]:
                found.append(f"{counts[severity]} {word}")
        parts.append("Found " + ", ".join(found) + " issue(s).")

        if counts["critical"]:
            parts.append(
                "Critical issues are the ones most likely to cause a refusal or a "
                "rejected submission. Fix those first."
            )

    if skipped:
        parts.append(
            f"{len(skipped)} check(s) could not be evaluated because the relevant "
            "document or field was missing or unreadable — these are listed "
            "separately and must not be read as having passed."
        )

    if degraded:
        parts.append(
            "Note: the AI review step did not run for this check, so letter-content "
            "findings are not included. All checklist, identity, financial and photo "
            "checks were still performed."
        )

    return " ".join(parts)


def overall_confidence(documents, issues: list[dict]) -> float:
    """How much the check trusts its own reading of the bundle."""
    doc_confidences = [
        float(getattr(d, "confidence", 0) or 0) for d in documents
    ]
    if not doc_confidences:
        return 0.0
    doc_part = sum(doc_confidences) / len(doc_confidences)

    if issues:
        issue_part = sum(float(i.get("confidence", 0.8)) for i in issues) / len(issues)
        return round(0.6 * doc_part + 0.4 * issue_part, 3)
    return round(doc_part, 3)
