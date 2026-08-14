"""Build a recovery plan from a decoded refusal.

The decoded grounds say what went wrong. This turns that into what to do next,
in the order it should be done, tied to the actual checklist for the corridor
the applicant is reapplying through.

Two judgements matter here and both are about honesty:

* Some grounds cannot be fixed by better paperwork — a SIS alert, a security
  objection, an allegation of a forged document. Selling those applicants a
  re-check would be taking money for something that cannot help. The plan says
  so and points at appeal instead.
* A refusal on "intention to leave" is the hardest ground to answer and the
  most common for high-refusal corridors. The plan should not imply that
  another bank statement fixes it.
"""

from __future__ import annotations

from . import grounds as G
from .decoder import Decoded

# Order to work through the grounds. Blocking ones first so the applicant
# learns immediately that reapplying is not their route; then the mechanically
# fixable, cheapest-to-fix first, because those are quick wins.
PRIORITY = {
    "false_document": 0,
    "sis_alert": 0,
    "public_policy_threat": 0,
    "no_insurance": 1,
    "insufficient_means": 2,
    "purpose_not_justified": 3,
    "info_not_reliable": 4,
    "doubts_document_authenticity": 5,
    "doubts_statements": 6,
    "already_stayed_90": 7,
    "revocation_requested": 8,
}


def _documents_for(pack: dict, rule_ids: set[str]) -> list[dict]:
    """Checklist entries implicated by the refusal, with their fix text."""
    out = []
    for spec in (pack or {}).get("documents", []):
        key = spec.get("key")
        if f"doc.{key}" in rule_ids:
            out.append(
                {
                    "key": key,
                    "label": spec.get("label") or key,
                    "why": spec.get("why"),
                    "fix": spec.get("fix"),
                    "authority": spec.get("authority"),
                }
            )
    return out


def _rules_for(pack: dict, rule_ids: set[str]) -> list[dict]:
    out = []
    for rule in (pack or {}).get("rules", []):
        if rule.get("id") in rule_ids:
            out.append(
                {
                    "id": rule.get("id"),
                    "title": rule.get("title"),
                    "fix": rule.get("fix"),
                    "authority": rule.get("authority"),
                }
            )
    return out


def build(decoded: Decoded, pack: dict | None = None) -> dict:
    """Turn a decoded refusal into an ordered plan."""
    pack = pack or {}
    steps: list[dict] = []

    ordered = sorted(decoded.grounds, key=lambda g: (PRIORITY.get(g.code, 50), g.number))

    for g in ordered:
        rule_ids = set(g.rule_ids)
        steps.append(
            {
                "ground_number": g.number,
                "ground_code": g.code,
                "title": g.plain,
                "official": g.official,
                "category": g.category,
                "fixable": g.fixable,
                "action": g.action,
                "appeal_note": g.appeal_note,
                "confidence": g.confidence,
                "evidence": g.evidence,
                "documents": _documents_for(pack, rule_ids),
                "rules": _rules_for(pack, rule_ids),
            }
        )

    blocking = [s for s in steps if not s["fixable"]]
    fixable = [s for s in steps if s["fixable"]]

    if not decoded.grounds:
        verdict = "undecoded"
        headline = "We could not identify the refusal grounds from this document."
        summary = (
            "Upload the official refusal form — the page with the numbered, ticked "
            "boxes — or select the grounds yourself, and we will build the plan."
        )
    elif blocking:
        verdict = "seek_advice"
        headline = "This refusal is not a paperwork problem."
        summary = (
            f"{len(blocking)} of the grounds given cannot be resolved by preparing a "
            "better file. Reapplying without addressing them would very likely fail "
            "again, and cost you another fee. Take advice about appealing."
        )
    elif any(s["ground_code"] == "doubts_statements" for s in fixable):
        verdict = "reapply_hard"
        headline = "You can reapply, but this needs more than tidier paperwork."
        summary = (
            "The consulate was not persuaded you would return home. That is answered "
            "with documented ties — approved leave with a return date, a registered "
            "business, property, dependants, prior compliant travel — not with a "
            "larger balance alone."
        )
    else:
        verdict = "reapply"
        headline = "This refusal is fixable."
        summary = (
            f"{len(fixable)} ground(s), all of them things you can put right before "
            "reapplying. Work through the steps below, then re-run the check to "
            "confirm the file is clean."
        )

    return {
        "verdict": verdict,
        "headline": headline,
        "summary": summary,
        "steps": steps,
        "blocking_count": len(blocking),
        "fixable_count": len(fixable),
        "can_recheck": bool(fixable) and not blocking,
        "consulate": decoded.consulate,
        "decision_date": decoded.decision_date,
        "method": decoded.method,
        "confidence": decoded.confidence,
        "notes": list(decoded.notes),
        "source": G.SOURCE,
    }


def appeal_guidance(decoded: Decoded) -> dict:
    """Whether appealing is worth considering, and the general shape of it."""
    if not decoded.grounds:
        return {"applicable": False}

    appealable = [g for g in decoded.grounds if g.appeal_note]
    return {
        "applicable": bool(appealable),
        "grounds": [
            {"number": g.number, "code": g.code, "note": g.appeal_note}
            for g in appealable
        ],
        "general": (
            "Every Schengen refusal carries a right of appeal against the member "
            "state that decided it, under that state's own law. The deadline and the "
            "authority are printed on your refusal letter — they are short, often "
            "15 to 30 days, so check the letter before doing anything else."
        ),
        "caution": (
            "An appeal argues the decision was wrong on the evidence you already "
            "gave. If your file genuinely was missing something, reapplying with a "
            "complete file is usually faster and more likely to succeed than "
            "appealing."
        ),
    }
