"""Parsing helpers for the messy strings OCR produces.

Two decisions worth stating:

* **Dates are day-first.** Both Pakistan and Europe write 03/04/2026 as
  3 April. Ambiguous dates are flagged, not silently guessed, because a
  misread travel date would produce a wrong finding.
* **Money keeps its currency.** A balance of "500,000" means nothing until we
  know whether it is PKR or EUR, so amounts without a currency are returned
  with ``currency=None`` and the rules engine treats them as unverified.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from dateutil import parser as dateparser

CURRENCY_SYMBOLS = {
    "€": "EUR", "£": "GBP", "$": "USD", "₨": "PKR", "﷼": "SAR", "₹": "INR",
    "¥": "JPY", "₺": "TRY", "د.إ": "AED",
}
CURRENCY_WORDS = {
    "euro": "EUR", "euros": "EUR", "eur": "EUR",
    "pound": "GBP", "pounds": "GBP", "sterling": "GBP", "gbp": "GBP",
    "dollar": "USD", "dollars": "USD", "usd": "USD", "us$": "USD",
    "rupee": "PKR", "rupees": "PKR", "pkr": "PKR", "rs": "PKR", "rs.": "PKR",
    "riyal": "SAR", "riyals": "SAR", "sar": "SAR", "sr": "SAR",
    "dirham": "AED", "aed": "AED",
}
KNOWN_CODES = {"EUR", "GBP", "USD", "PKR", "SAR", "AED", "INR", "TRY", "CHF", "CAD",
               "AUD", "JPY", "CNY", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF"}

_AMOUNT_RE = r"\d{1,3}(?:[,\s]\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?"


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )


def normalise_name(raw: str | None) -> str | None:
    """Upper-case, accent-free, punctuation-free, single-spaced."""
    if not raw:
        return None
    text = strip_accents(str(raw)).upper()
    text = re.sub(r"[^A-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


_TITLES = {"MR", "MRS", "MS", "MISS", "DR", "PROF", "SIR", "MADAM", "MSTR", "MASTER"}


def name_tokens(raw: str | None) -> list[str]:
    name = normalise_name(raw)
    if not name:
        return []
    return [t for t in name.split() if t not in _TITLES and len(t) > 1]


def names_match(a: str | None, b: str | None) -> tuple[bool, float, str]:
    """Compare two names tolerantly. Returns (match, similarity, reason).

    Real bundles legitimately differ: a ticket carries "MUHAMMAD ALI KHAN"
    while a bank statement carries "M. A. KHAN". We treat a name as matching
    when one token set is a subset of the other and the surname agrees.
    """
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False, 0.0, "missing"

    sa, sb = set(ta), set(tb)
    if sa == sb:
        return True, 1.0, "exact"

    overlap = len(sa & sb)
    union = len(sa | sb)
    similarity = overlap / union if union else 0.0

    if sa <= sb or sb <= sa:
        return True, max(similarity, 0.85), "subset"

    # Initial-expanded forms: "M" vs "MUHAMMAD".
    def expand(short: set[str], long: set[str]) -> bool:
        for tok in short:
            if len(tok) == 1 and not any(l.startswith(tok) for l in long):
                return False
        return True

    if ta[-1] == tb[-1]:  # surnames agree
        if expand(sa, sb) or expand(sb, sa):
            return True, max(similarity, 0.75), "surname+initials"
        return overlap >= 2, similarity, "surname match, given names differ"

    return False, similarity, "different"


def parse_date(raw: str | None, *, dayfirst: bool = True) -> date | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    try:
        parsed = dateparser.parse(text, dayfirst=dayfirst, fuzzy=True)
    except (ValueError, OverflowError, TypeError):
        return None
    if not parsed:
        return None
    if isinstance(parsed, datetime):
        parsed = parsed.date()
    # dateutil defaults missing components to today; reject absurd results.
    if parsed.year < 1900 or parsed.year > date.today().year + 30:
        return None
    return parsed


_DATE_PATTERNS = [
    r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b",
    r"\b\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}\b",
    r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{2,4}\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}\b",
]


def find_dates(text: str, limit: int = 60) -> list[date]:
    """All plausible dates in a blob, de-duplicated, in document order."""
    found: list[date] = []
    seen: set[date] = set()
    for pattern in _DATE_PATTERNS:
        for m in re.finditer(pattern, text, re.I):
            d = parse_date(m.group(0))
            if d and d not in seen:
                seen.add(d)
                found.append(d)
                if len(found) >= limit:
                    return found
    return found


def parse_amount(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = re.sub(r"[^\d.,\-]", "", str(raw))
    if not text:
        return None
    neg = text.startswith("-")
    text = text.lstrip("-")

    # Decide which separator is the decimal point by looking at the last one.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        # "1,234" is thousands; "12,34" is a European decimal.
        if len(parts[-1]) == 3 and all(len(p) <= 3 for p in parts[:-1]):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if neg else value


def detect_currency(text: str) -> str | None:
    """Most likely currency for a blob, by symbol/code/word frequency."""
    if not text:
        return None
    counts: dict[str, int] = {}

    for sym, code in CURRENCY_SYMBOLS.items():
        n = text.count(sym)
        if n:
            counts[code] = counts.get(code, 0) + n * 2

    for code in KNOWN_CODES:
        n = len(re.findall(rf"\b{code}\b", text, re.I))
        if n:
            counts[code] = counts.get(code, 0) + n * 3

    low = text.lower()
    for word, code in CURRENCY_WORDS.items():
        n = len(re.findall(rf"\b{re.escape(word)}\b", low))
        if n:
            counts[code] = counts.get(code, 0) + n

    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def find_amounts(text: str, limit: int = 400) -> list[float]:
    out: list[float] = []
    for m in re.finditer(_AMOUNT_RE, text):
        v = parse_amount(m.group(0))
        if v is not None:
            out.append(v)
        if len(out) >= limit:
            break
    return out


# Money as humans write it: thousands-separated, or with exactly two decimals.
# A bare digit run is excluded, which is what keeps account numbers, IBANs,
# policy numbers and phone numbers out of the transaction list.
_MONEY_RE = r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+\.\d{2}\b"


def find_transactions(text: str, limit: int = 500) -> list[float]:
    """Transaction amounts from a statement, excluding the balance column.

    Statement rows read ``date … description … amount … running balance``. The
    running balance climbs with every row, so treating the column as credits
    makes the largest one look like a single enormous deposit — which is
    exactly what the sudden-deposit rule is watching for, and would fire on
    every well-behaved account.

    The layout gives us the answer without needing to understand the columns:
    on a row carrying two or more amounts, the last one is the balance.
    """
    out: list[float] = []
    for line in text.splitlines():
        if not re.search(r"\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}", line):
            continue  # a row without a date is not a transaction row
        values = [
            parse_amount(m.group(0))
            for m in re.finditer(_MONEY_RE, line)
        ]
        values = [v for v in values if v is not None]
        if not values:
            continue
        candidates = values[:-1] if len(values) > 1 else values
        out.extend(candidates)
        if len(out) >= limit:
            break
    return out[:limit]


def find_money(text: str, limit: int = 400) -> list[float]:
    """Amounts that are formatted like currency. Stricter than find_amounts."""
    out: list[float] = []
    for m in re.finditer(_MONEY_RE, text):
        # Skip anything sitting immediately after an identifier label.
        prefix = text[max(0, m.start() - 40) : m.start()].lower()
        if re.search(r"(account|a/?c|iban|policy|reference|invoice|card)\s*"
                     r"(no|number|#)?\s*[:.\-]?\s*$", prefix):
            continue
        v = parse_amount(m.group(0))
        if v is not None:
            out.append(v)
        if len(out) >= limit:
            break
    return out


def amount_near(text: str, keywords: list[str], window: int = 140) -> float | None:
    """Find the amount closest after any of `keywords`. Used for balances."""
    low = text.lower()
    best: tuple[int, float] | None = None
    for kw in keywords:
        for m in re.finditer(re.escape(kw.lower()), low):
            segment = text[m.end() : m.end() + window]
            am = re.search(_AMOUNT_RE, segment)
            if not am:
                continue
            value = parse_amount(am.group(0))
            if value is None:
                continue
            distance = am.start()
            if best is None or distance < best[0]:
                best = (distance, value)
    return best[1] if best else None


def iso(d: date | None) -> str | None:
    return d.isoformat() if d else None
