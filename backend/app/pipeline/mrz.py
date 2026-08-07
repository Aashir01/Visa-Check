"""Machine Readable Zone parsing for passports (TD3) and ID cards (TD2).

Why this exists: the MRZ carries the passport number, name, nationality, date
of birth and expiry in a fixed-width format with ICAO 9303 check digits. That
makes it the one place in the whole bundle where we can extract identity
fields *and verify we read them correctly* — no LLM, no guessing.

Tesseract reliably confuses a handful of glyph pairs in the OCR-B font. When a
check digit fails we retry the field with those substitutions applied, which
recovers most real-world misreads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

# Glyph confusions, keyed by the character class the field expects.
_TO_DIGIT = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
                           "Z": "2", "S": "5", "B": "8", "G": "6", "T": "7"})
_TO_ALPHA = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"})

_WEIGHTS = (7, 3, 1)


@dataclass
class MrzResult:
    valid: bool = False
    format: str | None = None
    document_number: str | None = None
    surname: str | None = None
    given_names: str | None = None
    full_name: str | None = None
    nationality: str | None = None
    issuing_country: str | None = None
    date_of_birth: str | None = None      # ISO YYYY-MM-DD
    expiry_date: str | None = None        # ISO YYYY-MM-DD
    sex: str | None = None
    checks: dict = field(default_factory=dict)
    confidence: float = 0.0

    def as_dict(self) -> dict:
        return {
            k: v
            for k, v in {
                "document_number": self.document_number,
                "surname": self.surname,
                "given_names": self.given_names,
                "full_name": self.full_name,
                "nationality": self.nationality,
                "issuing_country": self.issuing_country,
                "date_of_birth": self.date_of_birth,
                "expiry_date": self.expiry_date,
                "sex": self.sex,
                "mrz_format": self.format,
                "mrz_valid": self.valid,
                "mrz_checks": self.checks,
            }.items()
            if v is not None
        }


def _char_value(ch: str) -> int:
    if ch.isdigit():
        return int(ch)
    if ch == "<":
        return 0
    if ch.isalpha():
        return ord(ch.upper()) - 55  # A=10 .. Z=35
    return 0


def compute_check_digit(payload: str) -> str:
    total = sum(_char_value(c) * _WEIGHTS[i % 3] for i, c in enumerate(payload))
    return str(total % 10)


def _verify(payload: str, expected: str) -> bool:
    return expected.isdigit() and compute_check_digit(payload) == expected


def _fix_and_verify(payload: str, expected: str, numeric: bool) -> tuple[str, str, bool]:
    """Try the raw read, then an OCR-corrected read, before giving up."""
    if _verify(payload, expected):
        return payload, expected, True

    fixed = payload.translate(_TO_DIGIT if numeric else _TO_ALPHA)
    fixed_expected = expected.translate(_TO_DIGIT)
    if _verify(fixed, fixed_expected):
        return fixed, fixed_expected, True

    # Mixed field (document numbers may be alphanumeric): only repair the
    # check digit itself.
    if _verify(payload, fixed_expected):
        return payload, fixed_expected, True

    return payload, expected, False


def _parse_yymmdd(raw: str, *, future_window: bool) -> str | None:
    """Expand a 2-digit MRZ year. Expiry looks forward, birth looks back."""
    raw = raw.translate(_TO_DIGIT)
    if not re.fullmatch(r"\d{6}", raw):
        return None
    yy, mm, dd = int(raw[0:2]), int(raw[2:4]), int(raw[4:6])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None

    current_yy = date.today().year % 100
    century = 2000 if future_window else (1900 if yy > current_yy else 2000)
    if future_window:
        # Expiries are within ~10 years, always this century for our purposes.
        century = 2000 if yy <= current_yy + 15 else 1900
    year = century + yy
    try:
        return date(year, mm, dd).isoformat()
    except ValueError:
        return None


def _clean_line(line: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", line.upper().replace(" ", ""))


def _split_names(field_str: str) -> tuple[str | None, str | None]:
    parts = field_str.split("<<", 1)
    surname = parts[0].replace("<", " ").strip() or None
    given = (parts[1].replace("<", " ").strip() if len(parts) > 1 else None) or None
    return surname, given


def _candidate_lines(text: str, length: int) -> list[tuple[str, str]]:
    """Find adjacent line pairs that look like an MRZ of the given width."""
    raw_lines = [_clean_line(ln) for ln in text.splitlines()]
    # Tolerate ±3 chars of OCR noise on the line width.
    lines = [ln for ln in raw_lines if abs(len(ln) - length) <= 3 and "<" in ln]
    pairs = []
    for i in range(len(raw_lines) - 1):
        a, b = raw_lines[i], raw_lines[i + 1]
        if abs(len(a) - length) <= 3 and abs(len(b) - length) <= 3 and "<" in a + b:
            pairs.append((a.ljust(length, "<")[:length], b.ljust(length, "<")[:length]))
    if not pairs and len(lines) >= 2:
        pairs.append(
            (lines[-2].ljust(length, "<")[:length], lines[-1].ljust(length, "<")[:length])
        )
    return pairs


def parse_mrz(text: str) -> MrzResult:
    """Parse the first plausible TD3 (passport) or TD2 MRZ found in `text`."""
    for length, fmt in ((44, "TD3"), (36, "TD2")):
        for l1, l2 in _candidate_lines(text, length):
            if not l1.startswith(("P", "I", "A", "C")):
                continue
            res = _parse_pair(l1, l2, fmt)
            if res and res.document_number:
                return res
    return MrzResult()


def _parse_pair(l1: str, l2: str, fmt: str) -> MrzResult | None:
    res = MrzResult(format=fmt)

    res.issuing_country = (l1[2:5].translate(_TO_ALPHA).replace("<", "") or None)
    res.surname, res.given_names = _split_names(l1[5:])
    if res.surname or res.given_names:
        res.full_name = " ".join(p for p in (res.given_names, res.surname) if p) or None

    doc_raw, doc_cd = l2[0:9], l2[9:10]
    doc, doc_cd, doc_ok = _fix_and_verify(doc_raw, doc_cd, numeric=False)
    res.document_number = doc.replace("<", "").strip() or None

    res.nationality = (l2[10:13].translate(_TO_ALPHA).replace("<", "") or None)

    dob_raw, dob_cd = l2[13:19], l2[19:20]
    dob, _, dob_ok = _fix_and_verify(dob_raw, dob_cd, numeric=True)
    res.date_of_birth = _parse_yymmdd(dob, future_window=False)

    sex = l2[20:21]
    res.sex = sex if sex in ("M", "F") else None

    exp_raw, exp_cd = l2[21:27], l2[27:28]
    exp, _, exp_ok = _fix_and_verify(exp_raw, exp_cd, numeric=True)
    res.expiry_date = _parse_yymmdd(exp, future_window=True)

    res.checks = {
        "document_number": doc_ok,
        "date_of_birth": dob_ok,
        "expiry_date": exp_ok,
    }
    passed = sum(1 for v in res.checks.values() if v)
    res.valid = passed == 3
    # Confidence tracks how many independent check digits agreed.
    res.confidence = round(0.35 + 0.2 * passed, 2) if res.document_number else 0.0
    return res
