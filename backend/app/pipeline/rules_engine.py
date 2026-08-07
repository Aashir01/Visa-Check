"""The rule engine.

A rule pack is data, not code (§1: "the moat is not the AI, it is the rule
packs"). Everything here is a deterministic evaluator over that data, so a
non-programmer editing a threshold in /admin/rules changes product behaviour
without a deploy.

Every issue carries the evidence that produced it — document, field and value
— so a report can always show *why* something was flagged. Findings never say
"approved"; the vocabulary is "no issue detected against checklist X vX.Y"
(§9).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from .doctypes import label_for
from .normalize import names_match, parse_date

SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
_MM_PER_INCH = 25.4


# --------------------------------------------------------------------------
# context
# --------------------------------------------------------------------------


@dataclass
class DocView:
    id: str
    doc_type: str
    filename: str
    fields: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    confidence: float = 0.0
    text: str = ""

    def get(self, name: str, default=None):
        value = self.fields.get(name, default)
        return default if value in ("", []) else value


@dataclass
class CheckContext:
    pack: dict
    profile: str
    documents: list[DocView]
    travel_start: date | None = None
    travel_end: date | None = None
    submission_date: date | None = None

    def __post_init__(self):
        self.submission_date = self.submission_date or date.today()
        self._by_type: dict[str, list[DocView]] = {}
        for d in self.documents:
            self._by_type.setdefault(d.doc_type, []).append(d)

    @property
    def present_types(self) -> set[str]:
        return set(self._by_type)

    def docs_of(self, doc_type: str) -> list[DocView]:
        return self._by_type.get(doc_type, [])

    def first(self, doc_type: str) -> DocView | None:
        docs = self.docs_of(doc_type)
        return docs[0] if docs else None

    def best(self, doc_type: str, field_name: str) -> tuple[DocView, object] | None:
        """The document of this type whose field is populated, if any."""
        for d in self.docs_of(doc_type):
            v = d.get(field_name)
            if v not in (None, "", []):
                return d, v
        return None

    @property
    def trip_days(self) -> int | None:
        if self.travel_start and self.travel_end:
            return max(1, (self.travel_end - self.travel_start).days + 1)
        # Fall back to the itinerary in the bundle.
        for dtype, a, b in (
            ("flight_ticket", "departure_date", "return_date"),
            ("hotel_booking", "check_in", "check_out"),
            ("invitation_letter", "stay_start", "stay_end"),
        ):
            doc = self.first(dtype)
            if not doc:
                continue
            start, end = parse_date(doc.get(a)), parse_date(doc.get(b))
            if start and end and end >= start:
                return max(1, (end - start).days + 1)
        default = self.pack.get("default_trip_days")
        return int(default) if default else None

    @property
    def effective_travel_start(self) -> date | None:
        if self.travel_start:
            return self.travel_start
        for dtype, f in (("flight_ticket", "departure_date"),
                         ("hotel_booking", "check_in"),
                         ("invitation_letter", "stay_start")):
            doc = self.first(dtype)
            if doc and (d := parse_date(doc.get(f))):
                return d
        return None

    @property
    def effective_travel_end(self) -> date | None:
        if self.travel_end:
            return self.travel_end
        for dtype, f in (("flight_ticket", "return_date"),
                         ("hotel_booking", "check_out"),
                         ("invitation_letter", "stay_end")):
            doc = self.first(dtype)
            if doc and (d := parse_date(doc.get(f))):
                return d
        return None


# --------------------------------------------------------------------------
# issues
# --------------------------------------------------------------------------


def make_issue(
    *,
    rule_id: str,
    severity: str,
    category: str,
    title: str,
    detail: str,
    fix: str,
    evidence: list | None = None,
    documents: list | None = None,
    confidence: float = 0.9,
) -> dict:
    return {
        "id": uuid.uuid4().hex[:12],
        "rule_id": rule_id,
        "severity": severity if severity in SEVERITY_ORDER else "warning",
        "category": category,
        "title": title,
        "detail": detail,
        "fix": fix,
        "evidence": evidence or [],
        "documents": documents or [],
        "confidence": round(float(confidence), 2),
    }


def _ev(doc: DocView | None, field_name: str | None = None, value=None) -> dict:
    return {
        "document_id": doc.id if doc else None,
        "document_type": doc.doc_type if doc else None,
        "document_label": label_for(doc.doc_type) if doc else None,
        "filename": doc.filename if doc else None,
        "field": field_name,
        "value": value,
    }


# --------------------------------------------------------------------------
# currency
# --------------------------------------------------------------------------


def convert(amount: float, from_ccy: str | None, to_ccy: str | None, fx: dict) -> tuple[float | None, str | None]:
    """Convert using the pack's indicative FX table.

    Returns (value, note). A missing rate returns (None, reason) so the caller
    reports "could not verify" rather than inventing a number.
    """
    if amount is None:
        return None, "no amount"
    if not from_ccy or not to_ccy or from_ccy == to_ccy:
        return amount, None

    base = (fx or {}).get("base")
    rates = (fx or {}).get("rates") or {}
    if not base:
        return None, "no FX table configured"

    def to_base(v: float, ccy: str) -> float | None:
        if ccy == base:
            return v
        rate = rates.get(ccy)
        return (v / rate) if rate else None

    def from_base(v: float, ccy: str) -> float | None:
        if ccy == base:
            return v
        rate = rates.get(ccy)
        return (v * rate) if rate else None

    in_base = to_base(amount, from_ccy)
    if in_base is None:
        return None, f"no rate for {from_ccy}"
    out = from_base(in_base, to_ccy)
    if out is None:
        return None, f"no rate for {to_ccy}"
    return round(out, 2), f"converted at indicative rate ({fx.get('updated', 'undated')})"


def money(value: float | None, ccy: str | None) -> str:
    if value is None:
        return "unknown"
    return f"{ccy + ' ' if ccy else ''}{value:,.0f}"


# --------------------------------------------------------------------------
# engine
# --------------------------------------------------------------------------


class RulesEngine:
    def __init__(self, pack: dict):
        self.pack = pack or {}
        self.fx = self.pack.get("fx") or {}
        self.weights = self.pack.get("severity_weights") or {
            "critical": 22, "warning": 8, "info": 2
        }

    # -- entry point -------------------------------------------------------

    def evaluate(self, ctx: CheckContext) -> tuple[list[dict], list[dict], list[dict]]:
        """Returns (issues, passed_checks, skipped_checks).

        A handler returning ``None`` means "I had nothing to evaluate against"
        — the document was absent, or the field could not be read. That is
        emphatically *not* a pass, and conflating the two is how a checker
        tells someone their file is fine when it never looked (§9). Skipped
        rules are reported separately so the user can see what went unchecked.
        """
        issues: list[dict] = []
        passed: list[dict] = []
        skipped: list[dict] = []

        issues.extend(self._missing_documents(ctx, passed))

        for rule in self.pack.get("rules", []):
            if not rule.get("enabled", True):
                continue
            if not self._applies(rule, ctx.profile):
                continue
            handler = getattr(self, f"_rule_{rule.get('type', '')}", None)
            if handler is None:
                continue

            try:
                produced = handler(rule, ctx)
            except Exception as exc:  # noqa: BLE001 - a bad rule must not kill the run
                produced = [
                    make_issue(
                        rule_id=rule.get("id", "unknown"),
                        severity="info",
                        category="engine",
                        title="A checklist rule could not be evaluated",
                        detail=f"Rule '{rule.get('id')}' failed: {exc}",
                        fix="This is a system issue, not a problem with your documents. "
                            "It has been logged for review.",
                        confidence=0.3,
                    )
                ]

            entry = {
                "rule_id": rule.get("id"),
                "title": rule.get("passed_label") or rule.get("title"),
                "category": rule.get("category", rule.get("type")),
            }
            if produced is None:
                skipped.append({**entry, "title": rule.get("title") or entry["title"]})
            elif produced:
                issues.extend(produced)
            else:
                passed.append(entry)

        issues.sort(key=lambda i: (SEVERITY_ORDER.get(i["severity"], 3), i["title"]))
        return issues, passed, skipped

    def _applies(self, rule: dict, profile: str) -> bool:
        profiles = rule.get("profiles") or ["*"]
        return "*" in profiles or profile in profiles

    # -- checklist ---------------------------------------------------------

    def _missing_documents(self, ctx: CheckContext, passed: list[dict]) -> list[dict]:
        issues = []
        present = ctx.present_types

        for spec in self.pack.get("documents", []):
            profiles = spec.get("profiles") or ["*"]
            if "*" not in profiles and ctx.profile not in profiles:
                continue

            key = spec.get("key")
            alternatives = spec.get("satisfied_by") or []
            candidates = [key, *alternatives]
            found = [c for c in candidates if c in present]

            if found:
                passed.append(
                    {
                        "rule_id": f"doc.{key}",
                        "title": f"{spec.get('label') or label_for(key)} provided",
                        "category": "checklist",
                    }
                )
                continue

            if not spec.get("required", False):
                if spec.get("recommend_if_missing"):
                    issues.append(
                        make_issue(
                            rule_id=f"doc.{key}",
                            severity="info",
                            category="missing_document",
                            title=f"Optional: {spec.get('label') or label_for(key)} not included",
                            detail=spec.get("why") or
                            "This document is not mandatory but strengthens an application.",
                            fix=spec.get("fix") or f"Consider adding your {spec.get('label') or label_for(key)}.",
                            confidence=0.9,
                        )
                    )
                continue

            label = spec.get("label") or label_for(key)
            alt_text = ""
            if alternatives:
                alt_text = " Accepted alternatives: " + ", ".join(
                    label_for(a) for a in alternatives
                ) + "."
            issues.append(
                make_issue(
                    rule_id=f"doc.{key}",
                    severity=spec.get("severity", "critical"),
                    category="missing_document",
                    title=f"Missing: {label}",
                    detail=(spec.get("why") or
                            f"The checklist for this corridor requires {label}.") + alt_text,
                    fix=spec.get("fix") or f"Add your {label} to the bundle and re-run the check.",
                    confidence=0.95,
                )
            )
        return issues

    # -- rule types --------------------------------------------------------

    def _rule_field_consistency(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """Same person, same details, across every document (§3.5)."""
        p = rule.get("params", {})
        field_name = p.get("field", "full_name")
        aliases: dict[str, str] = p.get("aliases", {})
        across = p.get("across") or []
        mode = p.get("mode", "name")  # name | exact | date

        observations: list[tuple[DocView, object]] = []
        for dtype in across:
            for doc in ctx.docs_of(dtype):
                key = aliases.get(dtype, field_name)
                value = doc.get(key)
                if value not in (None, "", []):
                    observations.append((doc, value))

        if len(observations) < 2:
            return None  # nothing to compare against

        reference_doc, reference = observations[0]
        # Prefer the passport as reference — its MRZ is check-digit verified.
        for doc, value in observations:
            if doc.doc_type == "passport":
                reference_doc, reference = doc, value
                break

        mismatches = []
        for doc, value in observations:
            if doc is reference_doc:
                continue
            if mode == "name":
                ok, _sim, _why = names_match(str(reference), str(value))
            elif mode == "date":
                ok = parse_date(str(reference)) == parse_date(str(value))
            else:
                ok = str(reference).strip().upper() == str(value).strip().upper()
            if not ok:
                mismatches.append((doc, value))

        if not mismatches:
            return []

        evidence = [_ev(reference_doc, field_name, reference)]
        evidence += [_ev(d, field_name, v) for d, v in mismatches]
        listed = "; ".join(
            f"{label_for(d.doc_type)}: \"{v}\"" for d, v in mismatches
        )
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "critical"),
                category="consistency",
                title=rule.get("title") or f"{field_name.replace('_', ' ').title()} does not match across documents",
                detail=(
                    f"Your {label_for(reference_doc.doc_type)} shows \"{reference}\", "
                    f"but {listed}. Consulates treat mismatched identity details as a "
                    "sign the file was assembled carelessly, or worse."
                ),
                fix=rule.get("fix") or (
                    "Make every document show the name exactly as it appears in your "
                    "passport. Where a third party issued the document (bank, employer, "
                    "airline), ask them to reissue it with the corrected spelling."
                ),
                evidence=evidence,
                documents=[d.id for d, _ in mismatches] + [reference_doc.id],
                confidence=0.85,
            )
        ]

    def _rule_financial_sufficiency(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """Balance vs the corridor's threshold (§3.6)."""
        p = rule.get("params", {})
        target_ccy = p.get("currency") or self.pack.get("currency")
        sources = p.get("source_documents") or ["bank_statement", "bank_letter"]

        found = None
        for dtype in sources:
            found = ctx.best(dtype, p.get("balance_field", "closing_balance"))
            if found:
                break

        if not found:
            return [
                make_issue(
                    rule_id=rule["id"],
                    severity=rule.get("severity", "critical"),
                    category="financial",
                    title="Bank balance could not be read",
                    detail=(
                        "No closing balance could be extracted from the financial "
                        "documents in this bundle. The check cannot confirm you meet "
                        "the funds requirement."
                    ),
                    fix=(
                        "Upload a clear, complete bank statement showing the closing "
                        "balance. A phone photo of a screen often fails to read — "
                        "download the PDF from your bank's app instead."
                    ),
                    confidence=0.6,
                )
            ]

        doc, balance = found
        balance = float(balance)
        source_ccy = doc.get("currency")

        days = ctx.trip_days
        method = p.get("method", "per_day")
        if method == "per_day":
            if not days:
                return [
                    make_issue(
                        rule_id=rule["id"],
                        severity="warning",
                        category="financial",
                        title="Trip length unknown, funds requirement not verified",
                        detail=(
                            "The funds requirement for this corridor is calculated per "
                            "day of stay, but no travel dates were found."
                        ),
                        fix="Enter your intended travel dates, or include a flight reservation.",
                        confidence=0.7,
                    )
                ]
            required = float(p.get("per_day_amount", 0)) * days
        elif method == "fixed":
            required = float(p.get("amount", 0))
        else:  # per_day_plus_fixed
            required = float(p.get("per_day_amount", 0)) * (days or 0) + float(
                p.get("amount", 0)
            )

        required = max(required, float(p.get("minimum_total", 0)))

        if not source_ccy:
            return [
                make_issue(
                    rule_id=rule["id"],
                    severity="warning",
                    category="financial",
                    title="Bank statement currency unclear",
                    detail=(
                        f"A balance of {balance:,.0f} was read, but the statement does "
                        "not clearly state its currency, so it cannot be compared "
                        f"against the requirement of {money(required, target_ccy)}."
                    ),
                    fix="Upload a statement that shows the account currency, or a bank "
                        "balance certificate that states it explicitly.",
                    evidence=[_ev(doc, "closing_balance", balance)],
                    documents=[doc.id],
                    confidence=0.6,
                )
            ]

        converted, note = convert(balance, source_ccy, target_ccy, self.fx)
        if converted is None:
            return [
                make_issue(
                    rule_id=rule["id"],
                    severity="warning",
                    category="financial",
                    title="Funds could not be compared to the requirement",
                    detail=f"Balance is {money(balance, source_ccy)} but {note}.",
                    fix="Ask your administrator to add an exchange rate for this "
                        "currency in the rule pack.",
                    evidence=[_ev(doc, "closing_balance", balance)],
                    documents=[doc.id],
                    confidence=0.5,
                )
            ]

        if converted >= required:
            return []

        shortfall = required - converted
        buffer_note = ""
        if converted >= required * 0.9:
            buffer_note = (
                " You are close to the threshold; consulates commonly expect a margin "
                "above the bare minimum rather than an exact figure."
            )

        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "critical"),
                category="financial",
                title="Bank balance is below the requirement for this trip",
                detail=(
                    f"Your statement shows {money(balance, source_ccy)}"
                    + (f" (≈ {money(converted, target_ccy)}{', ' + note if note else ''})"
                       if source_ccy != target_ccy else "")
                    + f". For {days} day(s) this corridor expects about "
                    f"{money(required, target_ccy)}, leaving a shortfall of "
                    f"{money(shortfall, target_ccy)}.{buffer_note}"
                ),
                fix=rule.get("fix") or (
                    "Either increase the balance well before you submit — funds that "
                    "appear days before submission attract suspicion — or add a "
                    "sponsor with an affidavit of support and their own statements."
                ),
                evidence=[
                    _ev(doc, "closing_balance", balance),
                    {"field": "required", "value": required, "currency": target_ccy},
                    {"field": "trip_days", "value": days},
                ],
                documents=[doc.id],
                confidence=0.8,
            )
        ]

    def _rule_statement_recency(self, rule: dict, ctx: CheckContext) -> list[dict]:
        p = rule.get("params", {})
        max_age = int(p.get("max_age_days", 30))
        found = ctx.best(p.get("document", "bank_statement"), p.get("field", "statement_date"))
        if not found:
            return None
        doc, raw = found
        stmt_date = parse_date(str(raw))
        if not stmt_date:
            return None
        age = (ctx.submission_date - stmt_date).days
        if age <= max_age:
            return []
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "warning"),
                category="financial",
                title="Bank statement is out of date",
                detail=(
                    f"The most recent entry is dated {stmt_date.isoformat()}, which is "
                    f"{age} days old. This corridor expects a statement no older than "
                    f"{max_age} days at submission."
                ),
                fix="Download a fresh statement, ideally stamped and signed by the bank, "
                    "dated within the last few days before your appointment.",
                evidence=[_ev(doc, "statement_date", stmt_date.isoformat())],
                documents=[doc.id],
                confidence=0.85,
            )
        ]

    def _rule_statement_history(self, rule: dict, ctx: CheckContext) -> list[dict]:
        p = rule.get("params", {})
        min_months = int(p.get("min_months", 3))
        doc = ctx.first(p.get("document", "bank_statement"))
        if not doc:
            return None
        start, end = parse_date(doc.get("period_start")), parse_date(doc.get("period_end"))
        if not (start and end):
            return None
        months = (end - start).days / 30.4
        if months + 0.2 >= min_months:
            return []
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "warning"),
                category="financial",
                title=f"Bank statement covers less than {min_months} months",
                detail=(
                    f"The statement runs {start.isoformat()} to {end.isoformat()}, about "
                    f"{months:.1f} months. This corridor expects at least {min_months} "
                    "months so the consulate can see a settled financial pattern rather "
                    "than a snapshot."
                ),
                fix=f"Request a statement covering the full last {min_months} months.",
                evidence=[
                    _ev(doc, "period_start", start.isoformat()),
                    _ev(doc, "period_end", end.isoformat()),
                ],
                documents=[doc.id],
                confidence=0.85,
            )
        ]

    def _rule_sudden_deposit(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """A large late deposit is the classic 'borrowed funds' refusal."""
        p = rule.get("params", {})
        ratio = float(p.get("ratio", 0.4))
        doc = ctx.first(p.get("document", "bank_statement"))
        if not doc:
            return None
        closing = doc.get("closing_balance")
        biggest = doc.get("max_transaction")
        if not closing or not biggest or float(closing) <= 0:
            return None
        share = float(biggest) / float(closing)
        # A share far above 1 means the figures disagree with each other, which
        # is a parsing problem rather than a finding worth alarming a user with.
        if share > 5:
            return None
        if share < ratio:
            return []
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "warning"),
                category="financial",
                title="A single large deposit dominates the balance",
                detail=(
                    f"The largest single amount on the statement is "
                    f"{money(float(biggest), doc.get('currency'))}, roughly "
                    f"{share * 100:.0f}% of the closing balance. Consulates read a "
                    "lump sum appearing shortly before submission as funds borrowed "
                    "for the application rather than genuine savings."
                ),
                fix=(
                    "Include documentary proof of where the money came from — a "
                    "property sale deed, gratuity letter, or the sender's own "
                    "statement. If the funds are a gift, add a sponsorship affidavit."
                ),
                evidence=[
                    _ev(doc, "max_transaction", biggest),
                    _ev(doc, "closing_balance", closing),
                ],
                documents=[doc.id],
                confidence=0.55,
            )
        ]

    def _rule_passport_validity(self, rule: dict, ctx: CheckContext) -> list[dict]:
        p = rule.get("params", {})
        doc = ctx.first("passport")
        if not doc:
            return None
        expiry = parse_date(doc.get("expiry_date"))
        if not expiry:
            return [
                make_issue(
                    rule_id=rule["id"],
                    severity="warning",
                    category="validity",
                    title="Passport expiry date could not be read",
                    detail="The passport expiry date was not extracted, so validity "
                           "could not be verified.",
                    fix="Upload a clearer scan of the passport bio-data page, including "
                        "the two machine-readable lines at the bottom.",
                    documents=[doc.id],
                    confidence=0.6,
                )
            ]

        issues = []
        min_days = int(p.get("min_days_after_return", 90))
        ref = ctx.effective_travel_end or ctx.submission_date
        required_until = ref + timedelta(days=min_days)
        if expiry < required_until:
            issues.append(
                make_issue(
                    rule_id=rule["id"],
                    severity=rule.get("severity", "critical"),
                    category="validity",
                    title="Passport does not stay valid long enough after your return",
                    detail=(
                        f"Your passport expires {expiry.isoformat()}. This corridor "
                        f"requires validity for at least {min_days} days beyond your "
                        f"intended departure from the destination "
                        f"({ref.isoformat()}), i.e. until at least "
                        f"{required_until.isoformat()}."
                    ),
                    fix="Renew your passport before applying. A renewal mid-application "
                        "usually means starting the application again.",
                    evidence=[_ev(doc, "expiry_date", expiry.isoformat())],
                    documents=[doc.id],
                    confidence=0.9,
                )
            )

        max_age_years = p.get("max_issue_age_years")
        issued = parse_date(doc.get("issue_date"))
        if max_age_years and issued:
            age_years = (ctx.submission_date - issued).days / 365.25
            if age_years > float(max_age_years):
                issues.append(
                    make_issue(
                        rule_id=rule["id"] + ".issue_age",
                        severity="warning",
                        category="validity",
                        title=f"Passport was issued more than {max_age_years} years ago",
                        detail=(
                            f"Issued {issued.isoformat()} ({age_years:.1f} years ago). "
                            f"Several consulates in this corridor will not accept a "
                            f"passport issued more than {max_age_years} years before "
                            "the application date."
                        ),
                        fix="Renew the passport, even if the expiry date has not yet passed.",
                        evidence=[_ev(doc, "issue_date", issued.isoformat())],
                        documents=[doc.id],
                        confidence=0.8,
                    )
                )
        return issues

    def _rule_date_coverage(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """One document's validity window must cover the whole trip."""
        p = rule.get("params", {})
        dtype = p.get("document", "travel_insurance")
        doc = ctx.first(dtype)
        if not doc:
            return None

        start = ctx.effective_travel_start
        end = ctx.effective_travel_end
        if not (start and end):
            return None

        valid_from = parse_date(doc.get(p.get("from_field", "valid_from")))
        valid_to = parse_date(doc.get(p.get("to_field", "valid_to")))
        if not (valid_from and valid_to):
            return None

        gaps = []
        if valid_from > start:
            gaps.append(f"cover begins {valid_from.isoformat()}, after your departure "
                        f"on {start.isoformat()}")
        if valid_to < end:
            gaps.append(f"cover ends {valid_to.isoformat()}, before your return on "
                        f"{end.isoformat()}")
        if not gaps:
            return []

        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "critical"),
                category="validity",
                title=rule.get("title") or f"{label_for(dtype)} does not cover the whole trip",
                detail="The policy dates leave your trip partly uncovered: " + "; ".join(gaps) + ".",
                fix=rule.get("fix") or (
                    "Ask the insurer to reissue the certificate covering every day of "
                    "travel, from departure to return inclusive."
                ),
                evidence=[
                    _ev(doc, "valid_from", valid_from.isoformat()),
                    _ev(doc, "valid_to", valid_to.isoformat()),
                ],
                documents=[doc.id],
                confidence=0.85,
            )
        ]

    def _rule_numeric_min(self, rule: dict, ctx: CheckContext) -> list[dict]:
        p = rule.get("params", {})
        dtype = p.get("document")
        field_name = p.get("field")
        minimum = float(p.get("min", 0))
        target_ccy = p.get("currency") or self.pack.get("currency")

        found = ctx.best(dtype, field_name)
        if not found:
            return None
        doc, raw = found
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None

        source_ccy = doc.get("currency") or target_ccy
        converted, note = convert(value, source_ccy, target_ccy, self.fx)
        if converted is None:
            return None
        if converted >= minimum:
            return []

        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "critical"),
                category="validity",
                title=rule.get("title") or f"{label_for(dtype)} is below the required minimum",
                detail=(
                    f"Found {money(value, source_ccy)}"
                    + (f" (≈ {money(converted, target_ccy)})" if source_ccy != target_ccy else "")
                    + f", but this corridor requires at least {money(minimum, target_ccy)}."
                ),
                fix=rule.get("fix") or "Obtain a document meeting the required minimum.",
                evidence=[_ev(doc, field_name, value)],
                documents=[doc.id],
                confidence=0.85,
            )
        ]

    def _rule_boolean_required(self, rule: dict, ctx: CheckContext) -> list[dict]:
        p = rule.get("params", {})
        dtype, field_name = p.get("document"), p.get("field")
        doc = ctx.first(dtype)
        if not doc:
            return None
        value = doc.get(field_name)
        if value is None:
            return None
        if bool(value) == bool(p.get("expected", True)):
            return []
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "warning"),
                category="validity",
                title=rule.get("title") or "A required feature is missing from a document",
                detail=rule.get("detail") or
                f"{label_for(dtype)} does not show '{field_name}'.",
                fix=rule.get("fix") or "Ask the issuer to include this explicitly.",
                evidence=[_ev(doc, field_name, value)],
                documents=[doc.id],
                confidence=0.7,
            )
        ]

    def _rule_date_order(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """Cross-document chronology, e.g. hotel dates inside the flight dates."""
        p = rule.get("params", {})
        a_doc = ctx.first(p.get("a_document"))
        b_doc = ctx.first(p.get("b_document"))
        if not (a_doc and b_doc):
            return None
        a = parse_date(a_doc.get(p.get("a_field")))
        b = parse_date(b_doc.get(p.get("b_field")))
        if not (a and b):
            return None

        tolerance = int(p.get("tolerance_days", 0))
        op = p.get("operator", "lte")
        ok = {
            "lte": a <= b + timedelta(days=tolerance),
            "gte": a + timedelta(days=tolerance) >= b,
            "eq": abs((a - b).days) <= tolerance,
        }.get(op, True)
        if ok:
            return []

        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "warning"),
                category="consistency",
                title=rule.get("title") or "Dates do not line up across your documents",
                detail=(rule.get("detail") or "Dates are inconsistent.")
                + f" {label_for(a_doc.doc_type)}: {a.isoformat()}; "
                f"{label_for(b_doc.doc_type)}: {b.isoformat()}.",
                fix=rule.get("fix") or "Align the dates across your itinerary documents.",
                evidence=[_ev(a_doc, p.get("a_field"), a.isoformat()),
                          _ev(b_doc, p.get("b_field"), b.isoformat())],
                documents=[a_doc.id, b_doc.id],
                confidence=0.8,
            )
        ]

    def _rule_document_age(self, rule: dict, ctx: CheckContext) -> list[dict]:
        p = rule.get("params", {})
        dtype = p.get("document")
        max_days = int(p.get("max_age_days", 90))
        found = ctx.best(dtype, p.get("field", "issue_date"))
        if not found:
            return None
        doc, raw = found
        issued = parse_date(str(raw))
        if not issued:
            return None
        age = (ctx.submission_date - issued).days
        if age <= max_days:
            return []
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "warning"),
                category="validity",
                title=rule.get("title") or f"{label_for(dtype)} is too old",
                detail=(
                    f"Dated {issued.isoformat()}, {age} days ago. This corridor expects "
                    f"it to be no more than {max_days} days old at submission."
                ),
                fix=rule.get("fix") or "Request a freshly dated copy from the issuer.",
                evidence=[_ev(doc, "issue_date", issued.isoformat())],
                documents=[doc.id],
                confidence=0.8,
            )
        ]

    def _rule_photo_spec(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """Photo compliance (§3.7). Thresholds come from the pack."""
        p = rule.get("params", {})
        doc = ctx.first("photo")
        if not doc:
            return None
        m = doc.metrics or {}
        if not m or m.get("error"):
            return [
                make_issue(
                    rule_id=rule["id"],
                    severity="warning",
                    category="photo",
                    title="Photograph could not be analysed",
                    detail=m.get("error") or "The image could not be read.",
                    fix="Upload the photo as a JPG or PNG straight from the studio, "
                        "not a screenshot or a scan of a printed copy.",
                    documents=[doc.id],
                    confidence=0.5,
                )
            ]

        issues: list[dict] = []
        sev = rule.get("severity", "warning")
        min_dpi = p.get("min_dpi")

        def flag(
            title: str,
            detail: str,
            fix: str,
            conf: float = 0.75,
            severity=None,
            measured: list[tuple[str, object]] | None = None,
        ):
            # Cite only the measurement this finding rests on. Dumping the whole
            # metrics dict onto every photo issue tells the reader nothing.
            issues.append(
                make_issue(
                    rule_id=f"{rule['id']}.{title[:24].lower().replace(' ', '_')}",
                    severity=severity or sev,
                    category="photo",
                    title=title,
                    detail=detail,
                    fix=fix,
                    evidence=[_ev(doc, field, value) for field, value in (measured or [])],
                    documents=[doc.id],
                    confidence=conf,
                )
            )

        # --- aspect ratio ---
        want_w, want_h = p.get("width_mm", 35), p.get("height_mm", 45)
        if want_w and want_h:
            target = want_w / want_h
            tol = float(p.get("aspect_tolerance", 0.06))
            ratio = m.get("aspect_ratio")
            if ratio and abs(ratio - target) > tol:
                flag(
                    "Photo is the wrong shape",
                    f"The image is {m.get('width_px')}×{m.get('height_px')}px, a ratio of "
                    f"{ratio:.2f}. A {want_w}×{want_h}mm photo has a ratio of {target:.2f}. "
                    "Cropping to the right shape now avoids a rejection at the counter.",
                    f"Crop or re-shoot to {want_w}mm × {want_h}mm.",
                    0.85,
                    measured=[("aspect_ratio", f"{ratio:.2f}"),
                              ("required_ratio", f"{target:.2f}")],
                )

        # --- resolution ---
        if min_dpi and m.get("dpi") and m["dpi"] < min_dpi:
            flag(
                "Photo resolution is too low",
                f"The file reports {m['dpi']} DPI; {min_dpi} DPI is expected.",
                f"Ask the studio for a {min_dpi} DPI file, or re-scan at that setting.",
                0.7,
                measured=[("dpi", m["dpi"]), ("required_dpi", min_dpi)],
            )
        # Derive the pixel floor from the physical spec so the two cannot
        # contradict each other: 45mm at 300 DPI is 531px, so a hard-coded
        # 600px floor would fail a perfectly compliant photo.
        min_px = p.get("min_height_px")
        if want_h and min_dpi:
            derived = int(round(want_h / _MM_PER_INCH * min_dpi))
            min_px = min(min_px, derived) if min_px else derived
        if min_px and m.get("height_px") and m["height_px"] < min_px:
            flag(
                "Photo is too small",
                f"The image is {m.get('width_px')}×{m.get('height_px')}px. A "
                f"{want_w}×{want_h}mm photo at {min_dpi or 300} DPI needs to be at "
                f"least {min_px}px tall to print correctly.",
                "Use the original full-size file rather than a resized or messaged copy.",
                0.8,
                measured=[("height_px", m["height_px"]), ("required_px", min_px)],
            )

        # --- face ---
        faces = m.get("faces", 0)
        if faces == 0:
            flag(
                "No face detected in the photograph",
                "Automatic detection found no face. This may mean the wrong file was "
                "uploaded, or the face is turned, shadowed, or partly covered.",
                "Upload a straight-on photo with the full face visible, eyes open, "
                "no headwear except for religious reasons and never covering the face.",
                0.6,
                measured=[("faces_detected", 0)],
            )
        elif faces > 1:
            flag(
                "More than one face detected",
                f"{faces} faces were detected. A visa photo must show only the applicant.",
                "Re-shoot against a plain wall with nobody else in frame.",
                0.6,
                measured=[("faces_detected", faces)],
            )
        else:
            fr = m.get("face_height_ratio")
            lo, hi = p.get("face_height_ratio", [0.6, 0.85])
            if fr and not (lo <= fr <= hi):
                too_small = fr < lo
                flag(
                    "Head size in the frame is outside the accepted range",
                    f"The face occupies about {fr * 100:.0f}% of the image height; this "
                    f"corridor expects {lo * 100:.0f}–{hi * 100:.0f}%. "
                    + ("The head is too small in frame." if too_small
                       else "The head is too large and may be cropped at the counter."),
                    "Reframe so the head, chin to crown, fills the required proportion.",
                    0.6,
                    measured=[("head_height_share", f"{fr * 100:.0f}%"),
                              ("accepted_range", f"{lo * 100:.0f}-{hi * 100:.0f}%")],
                )
            offset = m.get("face_centre_offset")
            if offset is not None and offset > float(p.get("max_centre_offset", 0.25)):
                flag(
                    "Face is not centred",
                    f"The face sits noticeably off-centre (offset {offset:.2f}).",
                    "Centre the head horizontally in the frame.",
                    0.55,
                    measured=[("centre_offset", f"{offset:.2f}")],
                )

        # --- background ---
        min_uniform = p.get("min_background_uniformity")
        if min_uniform and m.get("background_uniformity") is not None:
            if m["background_uniformity"] < float(min_uniform):
                flag(
                    "Background is not plain enough",
                    f"Background uniformity scored {m['background_uniformity']:.2f} "
                    f"(1.00 is perfectly plain). Patterns, furniture, shadows or "
                    "outdoor scenes behind the subject are the usual cause.",
                    "Re-shoot against a plain, evenly lit light-coloured wall with no "
                    "shadow behind the head.",
                    0.6,
                    measured=[("background_uniformity", m["background_uniformity"]),
                              ("required_minimum", min_uniform)],
                )
        bg_range = p.get("background_lightness_range")
        if bg_range and m.get("background_lightness") is not None:
            lo, hi = bg_range
            if not (lo <= m["background_lightness"] <= hi):
                flag(
                    "Background is the wrong tone",
                    f"Background lightness measured {m['background_lightness']:.2f}; "
                    f"this corridor expects {lo:.2f}–{hi:.2f} "
                    f"({'lighter' if m['background_lightness'] < lo else 'darker'} "
                    "than the requirement).",
                    "Use a plain white or light-grey background as the corridor requires.",
                    0.6,
                    measured=[("background_lightness", m["background_lightness"]),
                              ("accepted_range", f"{lo:.2f}-{hi:.2f}")],
                )

        # --- technical quality ---
        min_sharp = p.get("min_sharpness")
        if min_sharp and m.get("sharpness") is not None and m["sharpness"] < float(min_sharp):
            flag(
                "Photograph looks blurred",
                f"Sharpness scored {m['sharpness']:.0f}, below the {min_sharp} "
                "threshold. Blurred or low-quality photos are refused at submission.",
                "Upload the original studio file. Avoid photos sent over WhatsApp, "
                "which are heavily compressed.",
                0.65,
                measured=[("sharpness", m["sharpness"]), ("required_minimum", min_sharp)],
            )
        if p.get("must_be_colour") and m.get("is_greyscale"):
            flag(
                "Photograph appears to be black and white",
                "The image has almost no colour variation. Colour photographs are "
                "required.",
                "Submit the colour original.",
                0.7,
                measured=[("is_greyscale", True)],
            )
        return issues

    def _rule_profile_documents(self, rule: dict, ctx: CheckContext) -> list[dict]:
        """At least one of a set must be present, e.g. proof of income."""
        p = rule.get("params", {})
        any_of = p.get("any_of") or []
        if any(t in ctx.present_types for t in any_of):
            return []
        return [
            make_issue(
                rule_id=rule["id"],
                severity=rule.get("severity", "critical"),
                category="missing_document",
                title=rule.get("title") or "No proof of your stated status was found",
                detail=(rule.get("detail") or "")
                + " Accepted documents: "
                + ", ".join(label_for(t) for t in any_of)
                + ".",
                fix=rule.get("fix") or "Add at least one of the accepted documents.",
                confidence=0.9,
            )
        ]
