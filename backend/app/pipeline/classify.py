"""Document classification.

Keyword scoring first — it is free, instant, and correct on the large majority
of real bundles because these documents are highly formulaic. The LLM is asked
only about documents the keyword pass could not settle, and all of them go in
a single batched call rather than one call per file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import settings
from .doctypes import DOC_TYPES

# (regex, weight) per type. Weights are deliberately coarse: a strong marker
# such as an MRZ band or an IBAN outvotes any number of weak generic words.
SIGNATURES: dict[str, list[tuple[str, float]]] = {
    "passport": [
        (r"\bP<[A-Z]{3}", 6.0),
        (r"\bpassport\s*(no|number|#)", 3.5),
        (r"\brepublic of pakistan\b", 1.5),
        (r"\bplace of issue\b|\bdate of issue\b", 1.2),
        (r"\bnationality\b.{0,40}\bdate of birth\b", 1.5),
        (r"\bmachine readable\b", 2.0),
    ],
    "national_id": [
        (r"\bnational identity card\b|\bnadra\b|\bcnic\b", 4.0),
        (r"\b\d{5}-\d{7}-\d\b", 4.0),
    ],
    "bank_statement": [
        (r"\bstatement of account\b|\baccount statement\b", 5.0),
        (r"\b(opening|closing)\s+balance\b", 4.0),
        (r"\bdebit\b.{0,30}\bcredit\b", 2.5),
        (r"\bavailable balance\b|\bledger balance\b", 3.0),
        (r"\biban\b|\bswift\b", 1.5),
        (r"\btransaction (date|details)\b", 2.0),
        (r"\bwithdrawal(s)?\b.{0,30}\bdeposit(s)?\b", 2.0),
    ],
    "bank_letter": [
        (r"\bbalance certificate\b|\bcertificate of balance\b", 5.0),
        (r"\bto whom it may concern\b.{0,200}\baccount\b", 2.5),
        (r"\bmaintains an account\b", 3.5),
    ],
    "employment_letter": [
        (r"\bno objection certificate\b|\bNOC\b", 4.0),
        (r"\bis employed (with|at|by)\b|\bhas been working\b", 4.0),
        (r"\bleave (has been )?(granted|approved|sanctioned)\b", 4.0),
        (r"\bdesignation\b|\bjob title\b", 1.5),
        (r"\bmonthly (gross )?salary\b|\bannual salary\b", 2.0),
        (r"\bhuman resources?\b|\bHR department\b", 1.5),
    ],
    "salary_slip": [
        (r"\b(salary|pay)\s*(slip|stub)\b|\bpayslip\b", 5.0),
        (r"\bgross (pay|salary)\b.{0,60}\bnet (pay|salary)\b", 3.0),
        (r"\bdeductions?\b.{0,40}\ballowances?\b", 2.0),
    ],
    "business_registration": [
        (r"\bnational tax number\b|\bNTN\b", 3.5),
        (r"\bcertificate of incorporation\b|\bregistrar of companies\b", 4.5),
        (r"\bsole proprietor(ship)?\b|\bpartnership deed\b", 3.0),
        (r"\bchamber of commerce\b", 2.5),
    ],
    "tax_return": [
        (r"\bincome tax return\b|\btax year\b", 4.0),
        (r"\bFBR\b|\bfederal board of revenue\b", 4.0),
        (r"\btaxable income\b", 3.0),
    ],
    "student_enrollment": [
        (r"\bbonafide certificate\b|\benrol(l)?ment (letter|certificate)\b", 5.0),
        (r"\bis a (bona ?fide )?student\b", 4.0),
        (r"\bsemester\b|\bacademic year\b", 1.5),
        (r"\bregistration (no|number)\b.{0,40}\b(univ|college|school)", 2.0),
    ],
    "pension_statement": [
        (r"\bpension\b", 3.5),
        (r"\bretire(d|ment)\b", 2.0),
        (r"\bpension payment order\b|\bPPO\b", 4.0),
    ],
    "invitation_letter": [
        (r"\bletter of invitation\b|\binvitation letter\b", 5.0),
        (r"\bi (hereby )?invite\b|\bwould like to invite\b", 4.5),
        (r"\bmy (brother|sister|cousin|friend|uncle|aunt|son|daughter)\b", 2.0),
        (r"\bwill (stay|reside) (with me|at my)\b", 3.5),
        (r"\bverpflichtungserkl|\battestation d.accueil\b|\bcarta de invitaci", 5.0),
    ],
    "sponsor_letter": [
        (r"\baffidavit of support\b|\bsponsorship letter\b", 5.0),
        (r"\bi (will|shall) (bear|cover|be responsible for)\b.{0,60}\bexpenses\b", 4.5),
        (r"\bsponsor(ing|ship)?\b.{0,40}\b(trip|visit|travel|stay)\b", 3.0),
    ],
    "hotel_booking": [
        (r"\bbooking confirmation\b|\breservation confirmation\b", 4.5),
        (r"\bcheck[- ]?in\b.{0,60}\bcheck[- ]?out\b", 4.5),
        (r"\bbooking\.com\b|\bairbnb\b|\bagoda\b|\bexpedia\b|\bhotels?\.com\b", 4.0),
        (r"\bconfirmation number\b.{0,60}\b(hotel|room|guest)\b", 3.0),
        (r"\bnights?\b.{0,30}\broom\b", 1.5),
    ],
    "flight_ticket": [
        (r"\be-?ticket\b|\belectronic ticket\b", 5.0),
        (r"\bbooking reference\b|\bPNR\b|\brecord locator\b", 4.5),
        (r"\bflight (no|number)\b", 4.0),
        (r"\bdeparture\b.{0,50}\barrival\b", 2.5),
        (r"\b(IATA|airline) code\b|\bbaggage allowance\b", 2.0),
        (r"\b[A-Z]{3}\s*[-–→]\s*[A-Z]{3}\b", 2.0),
    ],
    "travel_insurance": [
        (r"\btravel (medical )?insurance\b", 5.0),
        (r"\binsurance (certificate|policy)\b", 4.5),
        (r"\bpolicy (no|number)\b", 3.0),
        (r"\brepatriation\b", 4.0),
        (r"\bmedical (expenses|cover(age)?)\b", 3.0),
        (r"\bsum insured\b|\bcoverage amount\b", 3.0),
        (r"\bschengen\b.{0,40}\binsurance\b", 4.0),
    ],
    "cover_letter": [
        (r"\bcover(ing)? letter\b", 4.5),
        (r"\bpurpose of (my )?(visit|travel|trip)\b", 4.0),
        (r"\bi am writing to (apply|request)\b", 3.5),
        (r"\bvisa officer\b|\bconsular (officer|section)\b|\bdear sir/?madam\b", 2.5),
    ],
    "application_form": [
        (r"\bapplication for schengen visa\b", 6.0),
        (r"\bvisa application form\b", 5.0),
        (r"\bVAF\b|\bform reference\b", 2.5),
        (r"\bfor official use only\b", 3.0),
    ],
    "previous_visa": [
        (r"\bvisa\b.{0,40}\b(issued|valid) (from|until)\b", 2.5),
        (r"\bmultiple entries?\b|\bsingle entry\b", 2.5),
        (r"\bduration of stay\b", 2.0),
    ],
    "marriage_certificate": [
        (r"\bmarriage (certificate|registration)\b|\bnikah ?nama\b", 5.0),
        (r"\bcertify that .{0,60}\bmarried\b", 3.5),
    ],
    "birth_certificate": [
        (r"\bbirth certificate\b|\bcertificate of birth\b", 5.0),
        (r"\bplace of birth\b.{0,60}\bfather.s name\b", 2.5),
    ],
    "property_document": [
        (r"\bproperty\b.{0,40}\b(deed|title|ownership)\b", 4.0),
        (r"\bregistry\b.{0,30}\bland\b|\bfard\b|\bjamabandi\b", 3.5),
        (r"\ballotment letter\b", 3.5),
    ],
    "police_certificate": [
        (r"\bpolice (clearance|character) certificate\b", 5.0),
        (r"\bno criminal record\b", 3.5),
    ],
    "vaccination_certificate": [
        (r"\bvaccination (certificate|record)\b", 4.5),
        (r"\bmeningococcal\b|\bmeningitis\b|\bACWY\b", 5.0),
        (r"\bpolio\b|\byellow fever\b", 3.0),
        (r"\bdose\b.{0,40}\bbatch (no|number)\b", 2.0),
    ],
    "mahram_proof": [
        (r"\bmahram\b", 5.0),
        (r"\brelationship (proof|certificate)\b", 2.5),
    ],
}

# Some cues are so specific they settle the type outright.
DECISIVE = {
    r"\bP<[A-Z]{3}[A-Z<]{5,}": "passport",
    r"\bapplication for schengen visa\b": "application_form",
}


@dataclass
class Classification:
    doc_type: str
    confidence: float
    source: str  # keyword | decisive | image | llm | fallback
    scores: dict[str, float] | None = None


def _score(text: str) -> dict[str, float]:
    low = text.lower()
    out: dict[str, float] = {}
    for dtype, sigs in SIGNATURES.items():
        total = 0.0
        for pattern, weight in sigs:
            if re.search(pattern, low, re.I):
                total += weight
        if total:
            out[dtype] = round(total, 2)
    return out


def classify_text(text: str) -> Classification:
    if not text or len(text.strip()) < 15:
        return Classification("unknown", 0.0, "fallback")

    for pattern, dtype in DECISIVE.items():
        if re.search(pattern, text, re.I):
            return Classification(dtype, 0.97, "decisive")

    scores = _score(text)
    if not scores:
        return Classification("unknown", 0.1, "keyword", scores)

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top, top_score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

    # Confidence rises with absolute evidence and with the margin over the
    # second-place type. Both matter: a bank letter and a bank statement share
    # vocabulary, so a narrow win should not read as certainty.
    strength = min(1.0, top_score / 9.0)
    margin = min(1.0, (top_score - runner_up) / 5.0) if top_score else 0.0
    confidence = round(min(0.95, 0.35 * strength + 0.45 * margin + 0.2 * strength), 2)
    return Classification(top, confidence, "keyword", scores)


def classify_image_without_text(metrics: dict | None) -> Classification:
    """Classify an image that carries no readable text.

    A document scan always yields text; a portrait does not. So a textless
    image is already strong evidence of the photograph, and the portrait
    aspect ratio settles it. Face detection *raises* confidence but is not
    required — a photo whose face cannot be found is precisely the case we
    want classified as a photo so the photo rules can flag it, rather than
    dropped as "unknown" where nothing checks it at all.
    """
    if not metrics:
        return Classification("unknown", 0.1, "image")

    ratio = metrics.get("aspect_ratio")
    faces = metrics.get("faces", 0) or 0
    portrait = bool(ratio and 0.6 <= ratio <= 0.92)

    if portrait and faces >= 1:
        return Classification("photo", 0.92, "image")
    if faces == 1 and (metrics.get("face_area_pct") or 0) > 8:
        return Classification("photo", 0.8, "image")
    if portrait:
        return Classification("photo", 0.7, "image")
    if faces >= 1:
        return Classification("photo", 0.6, "image")
    return Classification("unknown", 0.15, "image")


def classify_batch_with_llm(llm, pending: list[dict]) -> dict[str, Classification]:
    """Resolve ambiguous documents in one batched call."""
    if not pending or not llm.available:
        return {}

    catalogue = "\n".join(f"- {k}: {v}" for k, v in DOC_TYPES.items() if k != "unknown")
    blocks = []
    for item in pending:
        excerpt = (item["text"] or "")[:1200]
        blocks.append(
            f'<document id="{item["id"]}" filename="{item["filename"]}">\n'
            f"{excerpt}\n</document>"
        )

    result = llm.complete_json(
        kind="classification",
        system=(
            "You classify documents in a visa application bundle. Choose exactly "
            "one type per document from the catalogue. If nothing fits, use "
            '"unknown". Respond with JSON only: '
            '{"results":[{"id":"...","type":"...","confidence":0.0}]}'
        ),
        content=(
            f"Catalogue:\n{catalogue}\n\n"
            f"Classify each document below.\n\n" + "\n\n".join(blocks)
        ),
        max_tokens=1200,
    )

    out: dict[str, Classification] = {}
    if not isinstance(result, dict):
        return out
    for row in result.get("results", []) or []:
        doc_id, dtype = row.get("id"), row.get("type")
        if not doc_id or dtype not in DOC_TYPES:
            continue
        try:
            conf = float(row.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6
        out[str(doc_id)] = Classification(dtype, min(max(conf, 0.0), 0.95), "llm")
    return out


def needs_llm(c: Classification) -> bool:
    return c.doc_type == "unknown" or c.confidence < settings.low_confidence_threshold
