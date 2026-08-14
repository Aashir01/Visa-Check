"""Turn a refusal letter into a decoded, actionable result.

Strategy mirrors the rest of the pipeline: deterministic first, model second.

The Annex VI form is a fixed list of numbered boxes, so most of the work is
finding which numbers were ticked. That is pattern matching, not judgement, and
it costs nothing. The model is only asked when the deterministic pass finds
nothing — which mostly means a scanned form where the tick marks did not
survive OCR, or a member state that printed the reasons as prose.

A decoded refusal is worth more than the advice it produces. Every one is
ground truth about what a consulate actually refuses, which is the evidence the
rule packs have been missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import grounds as G


@dataclass
class DecodedGround:
    number: int
    code: str
    official: str
    plain: str
    category: str
    fixable: bool
    action: str
    appeal_note: str
    rule_ids: list[str] = field(default_factory=list)
    confidence: float = 0.9
    evidence: str = ""
    source: str = "pattern"     # pattern | keyword | llm | manual


@dataclass
class Decoded:
    grounds: list[DecodedGround] = field(default_factory=list)
    consulate: str | None = None
    decision_date: str | None = None
    appeal_deadline_note: str | None = None
    confidence: float = 0.0
    method: str = "none"
    notes: list[str] = field(default_factory=list)

    @property
    def codes(self) -> list[str]:
        return [g.code for g in self.grounds]

    @property
    def all_fixable(self) -> bool:
        return bool(self.grounds) and all(g.fixable for g in self.grounds)

    @property
    def has_blocking(self) -> bool:
        return any(not g.fixable for g in self.grounds)


# --------------------------------------------------------------------------
# deterministic pass
# --------------------------------------------------------------------------

# Distinctive phrases from each ground's official wording. Matching on these is
# what lets the decoder work on a letter whose tick marks did not survive OCR.
PHRASES: dict[str, tuple[str, ...]] = {
    "false_document": (
        r"false,?\s+counterfeit",
        r"forged travel document",
        r"counterfeit or forged",
    ),
    "purpose_not_justified": (
        r"purpose and conditions of the intended stay (?:were|was) not provided",
        r"justification for the purpose",
        r"purpose of (?:the )?(?:intended )?stay .{0,40}not (?:justified|provided)",
    ),
    "insufficient_means": (
        r"sufficient means of subsistence",
        r"means of subsistence",
        r"not in a position to acquire such means lawfully",
        r"proof of (?:your )?(?:sufficient )?financial means",
    ),
    "already_stayed_90": (
        r"already stayed for (?:90|three months|3 months)",
        r"180[- ]day period",
        r"current six[- ]month period",
    ),
    "sis_alert": (
        r"schengen information system",
        r"\bSIS\b.{0,40}refus",
        r"alert has been issued",
    ),
    "public_policy_threat": (
        r"threat to public policy",
        r"internal security, public health",
        r"international relations of one or more",
    ),
    "no_insurance": (
        r"travel medical insurance",
        r"medical insurance was not provided",
        r"adequate and valid travel medical",
    ),
    "info_not_reliable": (
        r"information submitted regarding the justification .{0,60}not reliable",
        r"was not reliable",
    ),
    "doubts_document_authenticity": (
        r"authenticity of the supporting documents",
        r"veracity of (?:their|its) contents",
        r"reasonable doubts as to the authenticity",
    ),
    "doubts_statements": (
        r"intention to leave the territory",
        r"reliability of the statements",
        r"intention to leave .{0,40}before the expiry",
    ),
    "revocation_requested": (
        r"revocation .{0,30}requested by the visa holder",
    ),
}

# A ticked box next to a number, in the shapes OCR tends to produce.
_TICK = r"(?:\[\s*[xX✓✔]\s*\]|\(\s*[xX✓✔]\s*\)|[xX✓✔]\s*|■|▪|●)"
_NUM_TICK = re.compile(
    rf"(?:^|\n)\s*{_TICK}?\s*(\d{{1,2}})\s*[.)\]]?\s+(?=\S)", re.MULTILINE
)


def _find_ticked_numbers(text: str) -> dict[int, str]:
    """Numbers that appear ticked. Only trust this when a tick is visible.

    Without a tick mark, a bare "3." is as likely to be a list item as a
    selected ground, so the phrase matcher below is the safer signal.
    """
    hits: dict[int, str] = {}
    for m in re.finditer(
        rf"(?:^|\n)\s*({_TICK})\s*(\d{{1,2}})\s*[.)\]]?\s*(.{{0,90}})",
        text,
        re.MULTILINE,
    ):
        number = int(m.group(2))
        if 1 <= number <= 11:
            hits[number] = m.group(0).strip()[:140]
    return hits


def _find_phrases(text: str) -> dict[str, str]:
    low = text.lower()
    found: dict[str, str] = {}
    for code, patterns in PHRASES.items():
        for pattern in patterns:
            m = re.search(pattern, low, re.I)
            if m:
                start = max(0, m.start() - 40)
                found[code] = text[start : m.end() + 60].replace("\n", " ").strip()
                break
    return found


_DATE = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{2,4})",
    re.I,
)


def _meta(text: str) -> tuple[str | None, str | None]:
    consulate = None
    m = re.search(
        r"(embassy|consulate(?: general)?|ambassade|konsulat)[^\n]{0,80}", text, re.I
    )
    if m:
        consulate = re.sub(r"\s+", " ", m.group(0)).strip()[:120]

    decision_date = None
    m = re.search(r"(?:date of (?:the )?decision|decision date|dated)\D{0,20}" + _DATE.pattern,
                  text, re.I)
    if m:
        decision_date = m.group(1)
    else:
        m = _DATE.search(text)
        if m:
            decision_date = m.group(1)
    return consulate, decision_date


def _build(code: str, *, confidence: float, evidence: str, source: str) -> DecodedGround | None:
    g = G.ground(code)
    if not g:
        return None
    return DecodedGround(
        number=g.number,
        code=g.code,
        official=g.official,
        plain=g.plain,
        category=g.category,
        fixable=g.fixable,
        action=g.action,
        appeal_note=g.appeal_note,
        rule_ids=list(g.rule_ids),
        confidence=confidence,
        evidence=evidence[:300],
        source=source,
    )


def decode_text(text: str) -> Decoded:
    """Deterministic decode. Returns an empty result if nothing was recognised."""
    result = Decoded()
    if not text or len(text.strip()) < 30:
        return result

    result.consulate, result.decision_date = _meta(text)

    ticked = _find_ticked_numbers(text)
    phrases = _find_phrases(text)

    chosen: dict[str, DecodedGround] = {}

    # A phrase match is the strongest signal: it quotes the ground itself.
    for code, evidence in phrases.items():
        built = _build(code, confidence=0.9, evidence=evidence, source="pattern")
        if built:
            chosen[code] = built

    # A ticked number corroborates a phrase, or stands alone at lower
    # confidence when the wording did not survive OCR.
    for number, evidence in ticked.items():
        g = G.BY_NUMBER.get(number)
        if not g:
            continue
        if g.code in chosen:
            chosen[g.code].confidence = 0.97
            chosen[g.code].source = "pattern+tick"
        else:
            built = _build(g.code, confidence=0.6, evidence=evidence, source="tick")
            if built:
                chosen[g.code] = built

    result.grounds = sorted(chosen.values(), key=lambda g: g.number)
    if result.grounds:
        result.method = "deterministic"
        result.confidence = round(
            sum(g.confidence for g in result.grounds) / len(result.grounds), 2
        )
    return result


# --------------------------------------------------------------------------
# model fallback
# --------------------------------------------------------------------------

SYSTEM = """You read visa refusal letters and identify which of the standard \
Schengen refusal grounds were given.

The Annex VI standard form has eleven numbered grounds. Identify ONLY the ones \
this letter actually gives. Rules:
- Never guess. If the letter is unclear, return an empty list.
- Do not infer a ground because it seems likely for this applicant.
- Letters may be in any language; translate mentally but report the ground numbers.
- Quote the fragment of the letter that supports each ground.

The eleven grounds:
1 false or forged travel document
2 purpose and conditions of the intended stay not justified
3 insufficient means of subsistence
4 already stayed 90 days in the current 180-day period
5 SIS alert for refusing entry
6 threat to public policy, internal security, public health or international relations
7 no adequate and valid travel medical insurance
8 information about the purpose of stay was not reliable
9 doubts about authenticity or veracity of supporting documents
10 doubts about reliability of statements or intention to leave before the visa expires
11 revocation requested by the visa holder

Respond with JSON only:
{"grounds":[{"number":3,"evidence":"quoted fragment","confidence":0.0}],
 "consulate":"...","decision_date":"YYYY-MM-DD"}"""


def decode_with_llm(llm, text: str) -> Decoded:
    result = Decoded()
    if not llm or not llm.available or not text.strip():
        return result

    payload = llm.complete_json(
        kind="refusal_decode",
        system=SYSTEM,
        content=f"Refusal letter:\n\n{text[:6000]}",
        max_tokens=1200,
    )
    if not isinstance(payload, dict):
        return result

    chosen = []
    for row in payload.get("grounds", []) or []:
        try:
            number = int(row.get("number"))
        except (TypeError, ValueError):
            continue
        g = G.BY_NUMBER.get(number)
        if not g:
            continue
        try:
            conf = float(row.get("confidence", 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        built = _build(
            g.code,
            # A model reading of a legal document should never present as
            # certain; the user can always correct it.
            confidence=min(max(conf, 0.3), 0.85),
            evidence=str(row.get("evidence") or "")[:300],
            source="llm",
        )
        if built:
            chosen.append(built)

    result.grounds = sorted(chosen, key=lambda g: g.number)
    result.consulate = (payload.get("consulate") or None)
    result.decision_date = (payload.get("decision_date") or None)
    if result.grounds:
        result.method = "llm"
        result.confidence = round(
            sum(g.confidence for g in result.grounds) / len(result.grounds), 2
        )
    return result


def decode(text: str, llm=None) -> Decoded:
    """Decode a refusal letter, deterministically where possible."""
    result = decode_text(text)
    if result.grounds:
        return result

    if llm is not None:
        result = decode_with_llm(llm, text)
        if result.grounds:
            result.notes.append(
                "The standard wording was not found in this letter, so the grounds "
                "were read by AI. Check them against your own copy."
            )
            return result

    result.notes.append(
        "No standard refusal ground could be identified in this document. If you "
        "have the official refusal form, upload that page — or select the ticked "
        "boxes yourself."
    )
    return result


def from_manual(codes) -> Decoded:
    """Build a result from grounds the user ticked themselves."""
    chosen = []
    for code in codes or ():
        g = G.ground(code)
        if g:
            built = _build(g.code, confidence=1.0, evidence="selected by you",
                           source="manual")
            if built:
                chosen.append(built)
    result = Decoded(grounds=sorted(chosen, key=lambda g: g.number))
    if chosen:
        result.method = "manual"
        result.confidence = 1.0
    return result
