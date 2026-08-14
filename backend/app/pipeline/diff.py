"""Compare a re-check against the check it answers.

Being told "you still have 4 issues" after an evening of fixing things is
demoralising and, worse, uninformative — the applicant cannot tell whether they
made progress. What they need is the delta: this is fixed, this is still open,
and this is new since last time.

Matching is by ``rule_id`` rather than by the issue's own id, because issue ids
are regenerated on every run. Photo rules append a suffix per finding
(``photo.spec.photo_is_too_small``), so those match on the full id too.
"""

from __future__ import annotations

SEVERITY_RANK = {"critical": 0, "warning": 1, "info": 2}


def _index(issues) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for issue in issues or []:
        key = issue.get("rule_id")
        if key:
            out[key] = issue
    return out


def _slim(issue: dict) -> dict:
    return {
        "rule_id": issue.get("rule_id"),
        "title": issue.get("title"),
        "severity": issue.get("severity"),
        "category": issue.get("category"),
        "fix": issue.get("fix"),
    }


def diff_checks(previous, current) -> dict:
    """What changed between two checks. Both are Check rows."""
    before = _index(getattr(previous, "issues", None))
    after = _index(getattr(current, "issues", None))

    resolved = [_slim(v) for k, v in before.items() if k not in after]
    remaining = [_slim(v) for k, v in after.items() if k in before]
    introduced = [_slim(v) for k, v in after.items() if k not in before]

    for group in (resolved, remaining, introduced):
        group.sort(key=lambda i: (SEVERITY_RANK.get(i["severity"], 3), i["title"] or ""))

    before_score = getattr(previous, "risk_score", None)
    after_score = getattr(current, "risk_score", None)
    delta = (
        after_score - before_score
        if before_score is not None and after_score is not None
        else None
    )

    def _crit(rows):
        return sum(1 for r in rows if r["severity"] == "critical")

    # Say plainly whether this file is ready, because that is the only question
    # the applicant is actually asking.
    open_critical = _crit(remaining) + _crit(introduced)
    if not after:
        headline = "Everything you were told to fix is now clear."
    elif open_critical:
        headline = (
            f"{open_critical} critical issue(s) still open — this file is not "
            "ready to submit yet."
        )
    elif resolved and not introduced:
        headline = (
            f"{len(resolved)} issue(s) fixed. What remains is not blocking, but "
            "worth reading before you submit."
        )
    elif introduced:
        headline = (
            f"{len(introduced)} new issue(s) appeared since the last check — "
            "check what changed in those documents."
        )
    else:
        headline = "No change since the previous check."

    return {
        "previous_check_id": getattr(previous, "id", None),
        "previous_score": before_score,
        "score": after_score,
        "score_delta": delta,
        "headline": headline,
        "resolved": resolved,
        "remaining": remaining,
        "introduced": introduced,
        "counts": {
            "resolved": len(resolved),
            "remaining": len(remaining),
            "introduced": len(introduced),
            "open_critical": open_critical,
        },
    }


def diff_against_refusal(refusal, current) -> dict:
    """Did the re-check clear the grounds the consulate actually refused on?

    A general improvement in score is not the question after a refusal. The
    question is narrower and more important: are the specific things they cited
    now fixed?
    """
    from ..refusal import ground as get_ground

    flagged = {
        i.get("rule_id") for i in (getattr(current, "issues", None) or [])
        if i.get("rule_id")
    }

    rows = []
    for code in (getattr(refusal, "ground_codes", None) or []):
        g = get_ground(code)
        if not g:
            continue
        still_open = sorted(set(g.rule_ids) & flagged)
        rows.append(
            {
                "code": code,
                "number": g.number,
                "plain": g.plain,
                "fixable": g.fixable,
                "cleared": not still_open and g.fixable,
                "still_open_rules": still_open,
            }
        )

    cleared = [r for r in rows if r["cleared"]]
    unresolved = [r for r in rows if not r["cleared"] and r["fixable"]]
    blocking = [r for r in rows if not r["fixable"]]

    if blocking:
        headline = (
            "Some grounds in your refusal cannot be answered with documents. "
            "This re-check does not address those."
        )
    elif unresolved:
        headline = (
            f"{len(unresolved)} of the grounds you were refused on still show "
            "problems in this file."
        )
    elif cleared:
        headline = (
            "Every ground you were refused on now checks clean against this "
            "corridor's checklist."
        )
    else:
        headline = "No refusal grounds were linked to this re-check."

    return {
        "refusal_id": getattr(refusal, "id", None),
        "headline": headline,
        "grounds": rows,
        "counts": {
            "cleared": len(cleared),
            "unresolved": len(unresolved),
            "blocking": len(blocking),
        },
    }
