"""Structured field extraction, deterministic first.

Each document type has a regex/heuristic extractor. Whatever those cannot
resolve is collected and sent to the LLM in **one batched call for the whole
bundle**, not one call per file — that is the difference between a check
costing cents and costing dollars (§9).

Deterministic values always win over LLM values: if the MRZ check digits agree
on a passport number, no model output overrides it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .mrz import parse_mrz
from .normalize import (
    amount_near,
    detect_currency,
    find_dates,
    find_transactions,
    iso,
    normalise_name,
    parse_amount,
    parse_date,
)

# Fields we want per type. Anything still missing after the deterministic pass
# becomes an LLM ask.
WANTED: dict[str, list[str]] = {
    "passport": ["full_name", "passport_number", "date_of_birth", "expiry_date",
                 "issue_date", "nationality", "place_of_birth"],
    "national_id": ["full_name", "id_number", "date_of_birth", "expiry_date"],
    "bank_statement": ["account_holder", "account_number", "bank_name", "currency",
                       "closing_balance", "opening_balance", "period_start",
                       "period_end", "statement_date"],
    "bank_letter": ["account_holder", "bank_name", "currency", "closing_balance",
                    "statement_date"],
    "employment_letter": ["employer_name", "employee_name", "designation",
                          "monthly_salary", "currency", "issue_date",
                          "leave_start", "leave_end", "joining_date"],
    "salary_slip": ["employee_name", "employer_name", "net_salary", "currency",
                    "period_end"],
    "student_enrollment": ["student_name", "institution", "issue_date", "programme"],
    "pension_statement": ["full_name", "monthly_amount", "currency", "issue_date"],
    "invitation_letter": ["host_name", "host_address", "guest_name", "issue_date",
                          "stay_start", "stay_end", "relationship"],
    "sponsor_letter": ["sponsor_name", "guest_name", "issue_date", "relationship"],
    "hotel_booking": ["guest_name", "hotel_name", "city", "check_in", "check_out",
                      "confirmation_number"],
    "flight_ticket": ["passenger_name", "booking_reference", "departure_date",
                      "return_date", "origin", "destination", "airline"],
    "travel_insurance": ["insured_name", "policy_number", "insurer", "currency",
                         "coverage_amount", "valid_from", "valid_to",
                         "covers_repatriation", "territory"],
    "cover_letter": ["applicant_name", "issue_date", "purpose", "travel_start",
                     "travel_end"],
    "application_form": ["full_name", "passport_number", "date_of_birth",
                         "travel_start", "travel_end"],
    "vaccination_certificate": ["full_name", "vaccine", "dose_date"],
    "marriage_certificate": ["spouse_a", "spouse_b", "marriage_date"],
    "birth_certificate": ["full_name", "date_of_birth", "father_name"],
    "police_certificate": ["full_name", "issue_date"],
}

DATE_FIELDS = {
    "date_of_birth", "expiry_date", "issue_date", "period_start", "period_end",
    "statement_date", "leave_start", "leave_end", "joining_date", "stay_start",
    "stay_end", "check_in", "check_out", "departure_date", "return_date",
    "valid_from", "valid_to", "travel_start", "travel_end", "dose_date",
    "marriage_date",
}
AMOUNT_FIELDS = {
    "closing_balance", "opening_balance", "monthly_salary", "net_salary",
    "coverage_amount", "monthly_amount",
}
NAME_FIELDS = {
    "full_name", "account_holder", "employee_name", "student_name", "guest_name",
    "passenger_name", "insured_name", "applicant_name", "host_name", "sponsor_name",
    "spouse_a", "spouse_b",
}


@dataclass
class Extraction:
    fields: dict = field(default_factory=dict)
    confidence: float = 0.0
    sources: dict = field(default_factory=dict)  # field -> mrz|regex|llm
    notes: list[str] = field(default_factory=list)

    def set(self, key: str, value, source: str, *, overwrite: bool = False) -> None:
        if value in (None, "", []):
            return
        if key in self.fields and not overwrite:
            return
        self.fields[key] = value
        self.sources[key] = source

    def missing(self, wanted: list[str]) -> list[str]:
        return [f for f in wanted if self.fields.get(f) in (None, "", [])]


# --------------------------------------------------------------------------
# deterministic extractors
# --------------------------------------------------------------------------


def _labelled(text: str, labels: list[str], window: int = 90) -> str | None:
    """Value following a label like 'Passport No.: AB1234567'.

    The label is wrapped non-capturing and anchored on a word boundary. Both
    matter: without the boundary, "ms" matches inside "SYSTEMS" and captures
    the rest of the company name as a person's name; without the non-capturing
    wrapper, any group inside a label pattern would shift the value group.
    """
    for label in labels:
        m = re.search(
            rf"\b(?:{label})\s*[:.\-—]?\s*(?P<val>[^\n\r]{{1,{window}}})",
            text,
            re.I,
        )
        if m:
            value = m.group("val").strip(" :.-\t")
            if value:
                return value
    return None


def _labelled_date(text: str, labels: list[str]):
    raw = _labelled(text, labels, window=40)
    return parse_date(raw) if raw else None


def extract_passport(text: str, ex: Extraction) -> None:
    mrz = parse_mrz(text)
    if mrz.document_number:
        for key, value in (
            ("passport_number", mrz.document_number),
            ("full_name", mrz.full_name),
            ("surname", mrz.surname),
            ("given_names", mrz.given_names),
            ("date_of_birth", mrz.date_of_birth),
            ("expiry_date", mrz.expiry_date),
            ("nationality", mrz.nationality),
            ("sex", mrz.sex),
        ):
            ex.set(key, value, "mrz")
        ex.fields["mrz_valid"] = mrz.valid
        ex.fields["mrz_checks"] = mrz.checks
        ex.confidence = max(ex.confidence, mrz.confidence)
        if not mrz.valid:
            ex.notes.append(
                "Passport MRZ check digits did not all validate — fields may be "
                "misread."
            )

    # Regex fallback / gap fill for anything the MRZ did not carry.
    num = _labelled(text, [r"passport\s*(?:no|number|#)", r"document\s*(?:no|number)"], 20)
    if num:
        cleaned = re.sub(r"[^A-Z0-9]", "", num.upper())[:12]
        if re.fullmatch(r"[A-Z]{0,3}\d{6,9}[A-Z]?", cleaned):
            ex.set("passport_number", cleaned, "regex")

    ex.set("full_name", normalise_name(_labelled(text, [r"(?:full\s*)?name", r"holder"], 60)), "regex")
    ex.set("date_of_birth", iso(_labelled_date(text, [r"date of birth", r"\bD\.?O\.?B\.?\b", r"born on"])), "regex")
    ex.set("expiry_date", iso(_labelled_date(text, [r"date of expiry", r"expiry date", r"valid until", r"expires? on"])), "regex")
    ex.set("issue_date", iso(_labelled_date(text, [r"date of issue", r"issue date", r"issued on"])), "regex")
    ex.set("place_of_birth", _labelled(text, [r"place of birth"], 40), "regex")
    ex.set("nationality", _labelled(text, [r"nationality"], 30), "regex")


def extract_bank_statement(text: str, ex: Extraction) -> None:
    currency = detect_currency(text)
    ex.set("currency", currency, "regex")

    closing = amount_near(text, ["closing balance", "balance c/f", "ending balance",
                                 "available balance", "closing bal"])
    opening = amount_near(text, ["opening balance", "balance b/f", "beginning balance",
                                 "opening bal"])
    ex.set("closing_balance", closing, "regex")
    ex.set("opening_balance", opening, "regex")

    ex.set("account_holder", normalise_name(
        _labelled(text, [r"account (?:holder|title|name)", r"customer name", r"title of account"], 60)
    ), "regex")
    ex.set("account_number", _labelled(text, [r"account\s*(?:no|number|#)", r"\bA/?C\s*(?:no|#)"], 30), "regex")
    ex.set("bank_name", _labelled(text, [r"bank name"], 60), "regex")

    period = re.search(
        r"(?:statement period|period|from)\s*[:\-]?\s*"
        r"([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})"
        r"\s*(?:to|-|–|until|through)\s*"
        r"([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
        text, re.I,
    )
    dates = find_dates(text)
    if period:
        ex.set("period_start", iso(parse_date(period.group(1))), "regex")
        ex.set("period_end", iso(parse_date(period.group(2))), "regex")
    elif len(dates) >= 2:
        ex.set("period_start", iso(min(dates)), "regex")
        ex.set("period_end", iso(max(dates)), "regex")
    if dates:
        ex.set("statement_date", iso(max(dates)), "regex")

    # Sudden-deposit detection: a balance that appears days before submission
    # is the single most common Schengen refusal trigger. Use the strict money
    # matcher so account and reference numbers never register as deposits, and
    # drop the balance figures themselves so a running balance column does not
    # masquerade as one enormous credit.
    transactions = find_transactions(text)
    balances = {v for v in (closing, opening) if v is not None}
    credits = [a for a in transactions if a > 0 and a not in balances]
    if credits:
        ex.fields.setdefault("max_transaction", max(credits))
    ex.fields.setdefault("transaction_count", len(transactions))
    ex.confidence = max(ex.confidence, 0.7 if closing is not None else 0.4)


def extract_flight_ticket(text: str, ex: Extraction) -> None:
    pnr = _labelled(text, [r"booking reference", r"\bPNR\b", r"record locator",
                           r"reservation code", r"booking code"], 20)
    if pnr:
        m = re.search(r"\b[A-Z0-9]{5,7}\b", pnr.upper())
        if m:
            ex.set("booking_reference", m.group(0), "regex")

    ex.set("passenger_name", normalise_name(
        _labelled(text, [r"passenger(?: name)?", r"traveller(?: name)?", r"name of passenger"], 60)
    ), "regex")
    ex.set("airline", _labelled(text, [r"airline", r"operated by", r"carrier"], 40), "regex")

    route = re.search(r"\b([A-Z]{3})\s*(?:[-–—>→]|to)\s*([A-Z]{3})\b", text)
    if route:
        ex.set("origin", route.group(1), "regex")
        ex.set("destination", route.group(2), "regex")

    dates = find_dates(text)
    if dates:
        future = sorted(d for d in dates)
        ex.set("departure_date", iso(future[0]), "regex")
        if len(future) > 1:
            ex.set("return_date", iso(future[-1]), "regex")
    ex.confidence = max(ex.confidence, 0.6 if dates else 0.3)


def extract_insurance(text: str, ex: Extraction) -> None:
    currency = detect_currency(text)
    ex.set("currency", currency, "regex")

    coverage = amount_near(text, ["sum insured", "coverage amount", "cover amount",
                                  "maximum benefit", "medical expenses", "coverage up to",
                                  "sum assured", "limit of indemnity"])
    if coverage is None:
        # Schengen mandates €30,000; that figure appearing at all is meaningful.
        m = re.search(r"\b(30[,.]?000|50[,.]?000|100[,.]?000)\b", text)
        if m:
            coverage = parse_amount(m.group(1))
    ex.set("coverage_amount", coverage, "regex")

    ex.set("policy_number", _labelled(text, [r"policy\s*(?:no|number|#)", r"certificate\s*(?:no|number)"], 30), "regex")
    ex.set("insured_name", normalise_name(
        _labelled(text, [r"insured(?: person| name)?", r"name of insured", r"policy ?holder"], 60)
    ), "regex")
    ex.set("insurer", _labelled(text, [r"insurer", r"insurance company", r"underwritten by"], 60), "regex")
    ex.set("covers_repatriation", bool(re.search(r"repatriation", text, re.I)), "regex")
    ex.set("territory", _labelled(text, [r"(?:area|territory) of (?:cover|validity)", r"geographical (?:area|scope)"], 60), "regex")

    valid = re.search(
        r"valid\s*(?:from)?\s*[:\-]?\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4})"
        r"\s*(?:to|-|–|until)\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4})",
        text, re.I,
    )
    dates = find_dates(text)
    if valid:
        ex.set("valid_from", iso(parse_date(valid.group(1))), "regex")
        ex.set("valid_to", iso(parse_date(valid.group(2))), "regex")
    elif len(dates) >= 2:
        ex.set("valid_from", iso(min(dates)), "regex")
        ex.set("valid_to", iso(max(dates)), "regex")
    ex.confidence = max(ex.confidence, 0.65 if coverage else 0.35)


def extract_hotel(text: str, ex: Extraction) -> None:
    ex.set("guest_name", normalise_name(_labelled(text, [r"guest(?: name)?", r"lead guest", r"booked by"], 60)), "regex")
    ex.set("hotel_name", _labelled(text, [r"hotel(?: name)?", r"property(?: name)?", r"accommodation"], 60), "regex")
    ex.set("confirmation_number", _labelled(text, [r"confirmation\s*(?:no|number|code)", r"booking\s*(?:no|number|id)"], 30), "regex")
    ex.set("city", _labelled(text, [r"city", r"location"], 40), "regex")

    ci = _labelled_date(text, [r"check[- ]?in", r"arrival"])
    co = _labelled_date(text, [r"check[- ]?out", r"departure"])
    dates = find_dates(text)
    ex.set("check_in", iso(ci or (min(dates) if dates else None)), "regex")
    ex.set("check_out", iso(co or (max(dates) if len(dates) > 1 else None)), "regex")


def extract_employment(text: str, ex: Extraction) -> None:
    # "This is to certify that Mr. AHMED KHAN is employed with ..." — capture
    # the name between the honorific and the verb rather than to end of line.
    m = re.search(
        r"\b(?:mr|ms|mrs|miss|dr)\.?\s+(?P<name>[A-Z][A-Za-z.\s]{3,50}?)\s+"
        r"(?:is|has been|was)\b",
        text,
    )
    if m:
        ex.set("employee_name", normalise_name(m.group("name")), "regex")
    ex.set("employee_name", normalise_name(
        _labelled(text, [r"employee name", r"this is to certify that"], 60)
    ), "regex")
    ex.set("employer_name", _labelled(text, [r"company(?: name)?", r"employer", r"organi[sz]ation"], 60), "regex")
    ex.set("designation", _labelled(text, [r"designation", r"job title", r"position(?: held)?", r"working as"], 50), "regex")
    ex.set("currency", detect_currency(text), "regex")
    ex.set("monthly_salary", amount_near(text, ["monthly salary", "gross salary", "salary of",
                                                "monthly gross", "drawing a salary"]), "regex")
    ex.set("issue_date", iso(_labelled_date(text, [r"date", r"dated"])), "regex")
    ex.set("joining_date", iso(_labelled_date(text, [r"(?:date of )?joining", r"employed since", r"working since"])), "regex")

    leave = re.search(
        r"leave\D{0,60}?([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4})"
        r"\s*(?:to|-|–|until|till)\s*([0-9]{1,2}[/\-.][0-9]{1,2}[/\-.][0-9]{2,4})",
        text, re.I,
    )
    if leave:
        ex.set("leave_start", iso(parse_date(leave.group(1))), "regex")
        ex.set("leave_end", iso(parse_date(leave.group(2))), "regex")
    ex.fields.setdefault("mentions_leave_approval",
                         bool(re.search(r"leave (?:has been )?(?:granted|approved|sanctioned)", text, re.I)))
    ex.fields.setdefault("mentions_return_assurance",
                         bool(re.search(r"(?:will|shall) (?:return|resume|rejoin)", text, re.I)))


def extract_invitation(text: str, ex: Extraction) -> None:
    ex.set("host_name", normalise_name(_labelled(text, [r"host(?: name)?", r"inviter", r"sincerely,?\s*"], 60)), "regex")
    ex.set("guest_name", normalise_name(_labelled(text, [r"invite[ds]?\s+(?:my\s+\w+\s+)?", r"guest(?: name)?", r"applicant"], 60)), "regex")
    ex.set("host_address", _labelled(text, [r"address", r"residing at", r"living at"], 120), "regex")
    ex.set("relationship", _labelled(text, [r"relationship", r"who is my", r"my\s+(brother|sister|cousin|friend|uncle|aunt|son|daughter|father|mother)"], 40), "regex")
    ex.set("issue_date", iso(_labelled_date(text, [r"date", r"dated"])), "regex")

    dates = find_dates(text)
    if len(dates) >= 2:
        ex.set("stay_start", iso(min(dates)), "regex")
        ex.set("stay_end", iso(max(dates)), "regex")


def extract_generic(text: str, ex: Extraction) -> None:
    ex.set("full_name", normalise_name(_labelled(text, [r"name"], 60)), "regex")
    ex.set("issue_date", iso(_labelled_date(text, [r"date", r"dated", r"issued on"])), "regex")


EXTRACTORS = {
    "passport": extract_passport,
    "national_id": extract_generic,
    "bank_statement": extract_bank_statement,
    "bank_letter": extract_bank_statement,
    "flight_ticket": extract_flight_ticket,
    "travel_insurance": extract_insurance,
    "hotel_booking": extract_hotel,
    "employment_letter": extract_employment,
    "salary_slip": extract_employment,
    "invitation_letter": extract_invitation,
    "sponsor_letter": extract_invitation,
}


def extract_document(doc_type: str | None, text: str) -> Extraction:
    ex = Extraction()
    if not text:
        return ex
    extractor = EXTRACTORS.get(doc_type or "", extract_generic)
    try:
        extractor(text, ex)
    except Exception as exc:  # noqa: BLE001 - one bad doc must not fail the check
        ex.notes.append(f"extraction error: {exc}")
    if ex.fields and not ex.confidence:
        ex.confidence = 0.5
    ex.fields["_dates_seen"] = [iso(d) for d in find_dates(text, limit=25)]
    return ex


# --------------------------------------------------------------------------
# batched LLM gap fill
# --------------------------------------------------------------------------


def llm_fill_gaps(llm, documents: list[dict]) -> dict[str, dict]:
    """One call for the whole bundle. `documents` carry id/type/text/missing."""
    asks = [d for d in documents if d.get("missing")]
    if not asks or not llm.available:
        return {}

    blocks = []
    for d in asks:
        blocks.append(
            f'<document id="{d["id"]}" type="{d["type"]}">\n'
            f'MISSING FIELDS: {", ".join(d["missing"])}\n'
            f'TEXT:\n{(d["text"] or "")[:3500]}\n</document>'
        )

    result = llm.complete_json(
        kind="extraction",
        system=(
            "You extract structured fields from visa application documents that "
            "have been OCR'd, so the text may contain errors.\n"
            "Rules:\n"
            "- Return a value ONLY if it is present in the text. Never infer, "
            "never guess, never fill from world knowledge.\n"
            "- Use null for anything not stated.\n"
            "- Dates: ISO YYYY-MM-DD. Source text is day-first (DD/MM/YYYY).\n"
            "- Amounts: plain numbers, no separators or symbols.\n"
            "- Names: exactly as written, no titles.\n"
            'Respond with JSON only: {"results":[{"id":"...","fields":{...},'
            '"confidence":0.0}]}'
        ),
        content="Extract the missing fields.\n\n" + "\n\n".join(blocks),
        max_tokens=2500,
    )

    out: dict[str, dict] = {}
    if not isinstance(result, dict):
        return out
    for row in result.get("results", []) or []:
        doc_id = str(row.get("id") or "")
        if not doc_id:
            continue
        fields = row.get("fields") or {}
        if not isinstance(fields, dict):
            continue
        try:
            conf = float(row.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6
        out[doc_id] = {"fields": _coerce(fields), "confidence": conf}
    return out


def _coerce(fields: dict) -> dict:
    """Normalise model output into the same shapes the regex path produces."""
    clean: dict = {}
    for key, value in fields.items():
        if value in (None, "", "null", "N/A", "n/a", "unknown"):
            continue
        if key in DATE_FIELDS:
            d = parse_date(str(value))
            if d:
                clean[key] = d.isoformat()
        elif key in AMOUNT_FIELDS:
            v = parse_amount(str(value))
            if v is not None:
                clean[key] = v
        elif key in NAME_FIELDS:
            n = normalise_name(str(value))
            if n:
                clean[key] = n
        else:
            clean[key] = value
    return clean
