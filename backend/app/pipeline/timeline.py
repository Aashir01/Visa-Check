"""What in this file goes stale, and when.

A visa file is not valid or invalid — it is valid *on a date*. A bank statement
that is 25 days old today is 46 days old at an appointment three weeks away,
and it is the appointment date the consulate applies. Applicants routinely
assemble a perfect file, wait six weeks for a slot, and submit documents that
quietly expired in the meantime.

This computes the expiry date of every time-bound document in the bundle and
compares it against the date the file will actually be submitted, so the report
can say "this is fine now, but not on your appointment date" — which is a thing
no checklist can tell you.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .doctypes import label_for
from .normalize import parse_date


@dataclass
class Entry:
    document_type: str
    label: str
    field: str
    what: str
    valid_until: date | None
    days_remaining: int | None
    status: str              # ok | expiring | expired | unknown
    detail: str

    def as_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "label": self.label,
            "field": self.field,
            "what": self.what,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "days_remaining": self.days_remaining,
            "status": self.status,
            "detail": self.detail,
        }


# Rules in the pack that impose an age limit tell us what expires and when.
# Reading them from the pack rather than hard-coding keeps the timeline correct
# when someone edits a threshold in /admin/rules.
def _age_limits(pack: dict) -> dict[tuple[str, str], tuple[int, str]]:
    limits: dict[tuple[str, str], tuple[int, str]] = {}
    for rule in (pack or {}).get("rules", []):
        p = rule.get("params") or {}
        rtype = rule.get("type")
        if rtype == "statement_recency":
            doc = p.get("document", "bank_statement")
            limits[(doc, p.get("field", "statement_date"))] = (
                int(p.get("max_age_days", 30)),
                "must be dated within this window at submission",
            )
        elif rtype == "document_age":
            doc = p.get("document")
            if doc:
                limits[(doc, p.get("field", "issue_date"))] = (
                    int(p.get("max_age_days", 90)),
                    "must be dated within this window at submission",
                )
    return limits


def build_timeline(ctx, pack: dict) -> list[dict]:
    """Every time-bound item in the bundle, dated against the submission date."""
    submission: date = ctx.submission_date or date.today()
    entries: list[Entry] = []

    def add(doc_type, field, what, until, detail_ok, detail_bad):
        if until is None:
            return
        remaining = (until - submission).days
        if remaining < 0:
            status = "expired"
            detail = detail_bad
        elif remaining <= 14:
            status = "expiring"
            detail = (
                f"{detail_ok} It is valid on your submission date, but only by "
                f"{remaining} day(s) — any delay puts it out of date."
            )
        else:
            status = "ok"
            detail = detail_ok
        entries.append(
            Entry(
                document_type=doc_type,
                label=label_for(doc_type),
                field=field,
                what=what,
                valid_until=until,
                days_remaining=remaining,
                status=status,
                detail=detail,
            )
        )

    # --- documents that expire on a stated date ---
    passport = ctx.first("passport")
    if passport:
        expiry = parse_date(passport.get("expiry_date"))
        add(
            "passport", "expiry_date", "Passport expiry", expiry,
            "Your passport is valid on your submission date.",
            "Your passport has already expired by your submission date.",
        )

    insurance = ctx.first("travel_insurance")
    if insurance:
        valid_to = parse_date(insurance.get("valid_to"))
        add(
            "travel_insurance", "valid_to", "Insurance cover ends", valid_to,
            "Your insurance is still in force on your submission date.",
            "Your insurance has already lapsed by your submission date.",
        )

    # --- documents that expire by age ---
    for (doc_type, field), (max_age, note) in _age_limits(pack).items():
        doc = ctx.first(doc_type)
        if not doc:
            continue
        issued = parse_date(doc.get(field))
        if not issued:
            continue
        until = issued + timedelta(days=max_age)
        add(
            doc_type, field, f"{label_for(doc_type)} goes out of date", until,
            f"Dated {issued.isoformat()}; it {note} and still qualifies on your "
            "submission date.",
            f"Dated {issued.isoformat()}; it {note}, and by your submission date "
            "it is too old. Get a freshly dated copy.",
        )

    entries.sort(
        key=lambda e: (e.valid_until or date.max, e.document_type)
    )
    return [e.as_dict() for e in entries]


def summarise(timeline: list[dict]) -> dict:
    """Headline counts, so the report can lead with the urgent thing."""
    expired = [t for t in timeline if t["status"] == "expired"]
    expiring = [t for t in timeline if t["status"] == "expiring"]
    soonest = min(
        (t for t in timeline if t["days_remaining"] is not None),
        key=lambda t: t["days_remaining"],
        default=None,
    )
    return {
        "total": len(timeline),
        "expired": len(expired),
        "expiring": len(expiring),
        "soonest": soonest,
    }
