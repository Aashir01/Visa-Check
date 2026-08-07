"""Unit tests for the deterministic core.

These cover the parts where a wrong answer costs a user their visa fee: MRZ
check digits, name matching, money parsing, and the rule handlers' pass /
fail / could-not-evaluate distinction.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.pipeline import normalize
from app.pipeline.mrz import compute_check_digit, parse_mrz
from app.pipeline.rules_engine import CheckContext, DocView, RulesEngine, convert
from app.pipeline.scoring import score_check
from app.rulepack_schema import validate_pack

PACK_DIR = Path(__file__).resolve().parent.parent / "app" / "rulepacks"


# --------------------------------------------------------------------------
# MRZ
# --------------------------------------------------------------------------


def _mrz_lines(passport="AB1234567", surname="KHAN", given="AHMED RAZA",
               dob=date(1990, 4, 12), expiry=date(2030, 4, 11)):
    from tests.make_fixtures import build_mrz

    return build_mrz(passport, surname, given, dob, expiry)


def test_check_digit_matches_icao_example():
    # ICAO 9303 worked example.
    assert compute_check_digit("D23145890734") == "9"


def test_mrz_round_trip():
    l1, l2 = _mrz_lines()
    result = parse_mrz(f"some header\n{l1}\n{l2}\n")
    assert result.valid is True
    assert result.document_number == "AB1234567"
    assert result.surname == "KHAN"
    assert result.given_names == "AHMED RAZA"
    assert result.date_of_birth == "1990-04-12"
    assert result.expiry_date == "2030-04-11"
    assert result.nationality == "PAK"


def test_mrz_recovers_common_ocr_confusion():
    """Tesseract reads O for 0 in the date fields; check digits catch it."""
    l1, l2 = _mrz_lines(dob=date(1990, 4, 12))
    # Corrupt the DOB digits the way OCR-B misreads them.
    corrupted = l2[:13] + l2[13:19].replace("0", "O") + l2[19:]
    result = parse_mrz(f"{l1}\n{corrupted}")
    assert result.date_of_birth == "1990-04-12"
    assert result.checks["date_of_birth"] is True


def test_mrz_absent_returns_empty():
    assert parse_mrz("just some ordinary letter text").document_number is None


# --------------------------------------------------------------------------
# names
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("AHMED RAZA KHAN", "AHMED RAZA KHAN", True),
        ("Ahmed Raza Khan", "AHMED RAZA KHAN", True),
        ("AHMED RAZA KHAN", "Mr. Ahmed Raza Khan", True),
        ("AHMED RAZA KHAN", "AHMED KHAN", True),          # subset
        ("AHMED RAZA KHAN", "A R KHAN", True),            # initials
        ("AHMED RAZA KHAN", "AHMAD R KHANN", False),      # misspelling
        ("AHMED RAZA KHAN", "FATIMA BIBI", False),
    ],
)
def test_names_match(a, b, expected):
    assert normalize.names_match(a, b)[0] is expected


# --------------------------------------------------------------------------
# money and dates
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1,250,000.00", 1_250_000.0),
        ("EUR 30,000", 30_000.0),
        ("1.234.567,89", 1_234_567.89),   # European grouping
        ("500", 500.0),
        ("PKR 385,000", 385_000.0),
    ],
)
def test_parse_amount(raw, expected):
    assert normalize.parse_amount(raw) == pytest.approx(expected)


def test_find_transactions_excludes_running_balance():
    """The last amount on a statement row is the balance, not a deposit."""
    text = (
        "Account Number: 0123456789012\n"
        "01/03/2026  Salary credit   18,000.00   1,268,000.00\n"
        "08/03/2026  Salary credit   18,000.00   1,286,000.00\n"
    )
    values = normalize.find_transactions(text)
    assert 18_000.0 in values
    assert 1_286_000.0 not in values          # running balance excluded
    assert 123456789012.0 not in values       # account number excluded


def test_find_money_skips_identifier_numbers():
    assert normalize.find_money("Policy Number: 55,021") == []


def test_parse_date_is_day_first():
    assert normalize.parse_date("03/04/2026") == date(2026, 4, 3)
    assert normalize.parse_date("2026-04-03") == date(2026, 4, 3)


def test_detect_currency():
    assert normalize.detect_currency("Closing Balance: PKR 1,250,000") == "PKR"
    assert normalize.detect_currency("Sum Insured: EUR 30,000") == "EUR"


# --------------------------------------------------------------------------
# currency conversion
# --------------------------------------------------------------------------


def test_convert_uses_pack_rates():
    fx = {"base": "EUR", "rates": {"PKR": 315.0}}
    value, _ = convert(315_000, "PKR", "EUR", fx)
    assert value == pytest.approx(1000.0)


def test_convert_reports_missing_rate_rather_than_guessing():
    value, note = convert(1000, "XYZ", "EUR", {"base": "EUR", "rates": {}})
    assert value is None
    assert "no rate" in note


# --------------------------------------------------------------------------
# rules engine
# --------------------------------------------------------------------------


def _pack(rules, documents=None):
    return {
        "version": "test",
        "title": "Test corridor",
        "currency": "EUR",
        "fx": {"base": "EUR", "rates": {"PKR": 315.0}},
        "documents": documents if documents is not None
        else [{"key": "passport", "label": "Passport", "required": True,
               "fix": "Add it."}],
        "rules": rules,
    }


def _ctx(pack, docs, **kw):
    return CheckContext(pack=pack, profile="employed", documents=docs, **kw)


def test_missing_required_document_is_critical():
    pack = _pack([])
    issues, passed, skipped = RulesEngine(pack).evaluate(_ctx(pack, []))
    assert len(issues) == 1
    assert issues[0]["severity"] == "critical"
    assert "Passport" in issues[0]["title"]


def test_satisfied_by_alternative_counts_as_present():
    pack = _pack([], documents=[{
        "key": "bank_statement", "label": "Bank statement", "required": True,
        "satisfied_by": ["bank_letter"], "fix": "Add it.",
    }])
    docs = [DocView(id="1", doc_type="bank_letter", filename="letter.pdf")]
    issues, passed, _ = RulesEngine(pack).evaluate(_ctx(pack, docs))
    assert issues == []
    assert len(passed) == 1


def test_name_mismatch_is_reported_with_evidence():
    rule = {
        "id": "consistency.name", "type": "field_consistency", "severity": "critical",
        "title": "Name mismatch",
        "params": {"field": "full_name", "mode": "name",
                   "across": ["passport", "bank_statement"],
                   "aliases": {"bank_statement": "account_holder"}},
    }
    pack = _pack([rule], documents=[])
    docs = [
        DocView(id="1", doc_type="passport", filename="p.pdf",
                fields={"full_name": "AHMED RAZA KHAN"}),
        DocView(id="2", doc_type="bank_statement", filename="b.pdf",
                fields={"account_holder": "AHMAD R KHANN"}),
    ]
    issues, _, _ = RulesEngine(pack).evaluate(_ctx(pack, docs))
    assert len(issues) == 1
    assert issues[0]["severity"] == "critical"
    assert any(e["value"] == "AHMAD R KHANN" for e in issues[0]["evidence"])


def test_single_document_cannot_be_inconsistent_and_is_not_a_pass():
    """The crux: nothing to compare must not read as 'verified'."""
    rule = {
        "id": "consistency.name", "type": "field_consistency",
        "title": "Name mismatch",
        "params": {"field": "full_name", "mode": "name",
                   "across": ["passport", "bank_statement"]},
    }
    pack = _pack([rule], documents=[])
    docs = [DocView(id="1", doc_type="passport", filename="p.pdf",
                    fields={"full_name": "AHMED RAZA KHAN"})]
    issues, passed, skipped = RulesEngine(pack).evaluate(_ctx(pack, docs))
    assert issues == []
    assert passed == []
    assert len(skipped) == 1


def test_photo_rule_skipped_when_no_photo_uploaded():
    rule = {"id": "photo.spec", "type": "photo_spec", "title": "Photo",
            "params": {"width_mm": 35, "height_mm": 45}}
    pack = _pack([rule], documents=[])
    issues, passed, skipped = RulesEngine(pack).evaluate(_ctx(pack, []))
    assert passed == []
    assert len(skipped) == 1


def test_passport_validity_flags_short_validity():
    rule = {"id": "passport.validity", "type": "passport_validity",
            "severity": "critical", "title": "Validity",
            "params": {"min_days_after_return": 90}}
    pack = _pack([rule], documents=[])
    ret = date.today() + timedelta(days=30)
    docs = [DocView(id="1", doc_type="passport", filename="p.pdf",
                    fields={"expiry_date": (ret + timedelta(days=20)).isoformat()})]
    issues, _, _ = RulesEngine(pack).evaluate(
        _ctx(pack, docs, travel_start=date.today() + timedelta(days=20), travel_end=ret)
    )
    assert len(issues) == 1
    assert issues[0]["severity"] == "critical"


def test_financial_sufficiency_converts_currency():
    rule = {
        "id": "fin", "type": "financial_sufficiency", "severity": "critical",
        "title": "Funds",
        "params": {"method": "per_day", "per_day_amount": 100, "currency": "EUR",
                   "source_documents": ["bank_statement"]},
    }
    pack = _pack([rule], documents=[])
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=9)   # 10 days -> EUR 1000 required

    rich = [DocView(id="1", doc_type="bank_statement", filename="b.pdf",
                    fields={"closing_balance": 1_000_000, "currency": "PKR"})]
    issues, _, _ = RulesEngine(pack).evaluate(
        _ctx(pack, rich, travel_start=start, travel_end=end)
    )
    assert issues == []   # PKR 1,000,000 ~ EUR 3174

    poor = [DocView(id="1", doc_type="bank_statement", filename="b.pdf",
                    fields={"closing_balance": 100_000, "currency": "PKR"})]
    issues, _, _ = RulesEngine(pack).evaluate(
        _ctx(pack, poor, travel_start=start, travel_end=end)
    )
    assert len(issues) == 1
    assert "below the requirement" in issues[0]["title"]


def test_insurance_must_cover_whole_trip():
    rule = {"id": "ins.dates", "type": "date_coverage", "severity": "critical",
            "title": "Cover", "params": {"document": "travel_insurance"}}
    pack = _pack([rule], documents=[])
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=10)
    docs = [DocView(id="1", doc_type="travel_insurance", filename="i.pdf",
                    fields={"valid_from": start.isoformat(),
                            "valid_to": (end - timedelta(days=3)).isoformat()})]
    issues, _, _ = RulesEngine(pack).evaluate(
        _ctx(pack, docs, travel_start=start, travel_end=end)
    )
    assert len(issues) == 1
    assert "before your return" in issues[0]["detail"]


def test_broken_rule_does_not_crash_the_check():
    rule = {"id": "bad", "type": "numeric_min", "title": "Bad",
            "params": {"document": "travel_insurance", "field": "coverage_amount",
                       "min": "not-a-number"}}
    pack = _pack([rule], documents=[])
    docs = [DocView(id="1", doc_type="travel_insurance", filename="i.pdf",
                    fields={"coverage_amount": 30000})]
    issues, _, _ = RulesEngine(pack).evaluate(_ctx(pack, docs))
    assert all(i["severity"] == "info" for i in issues)


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------


def _issues(**counts):
    out = []
    for severity, n in counts.items():
        for i in range(n):
            out.append({"severity": severity, "confidence": 0.9, "title": f"{severity}{i}"})
    return out


def test_clean_bundle_scores_high():
    result = score_check([])
    assert result["score"] == 100
    assert result["band"] == "low"


def test_any_critical_caps_the_band():
    result = score_check(_issues(critical=1))
    assert result["score"] <= 64
    assert result["band"] != "low"


def test_score_is_monotonic_in_severity():
    a = score_check(_issues(info=3))["score"]
    b = score_check(_issues(warning=3))["score"]
    c = score_check(_issues(critical=3))["score"]
    assert a > b > c


def test_score_never_leaves_range():
    result = score_check(_issues(critical=40, warning=40, info=40))
    assert 0 <= result["score"] <= 100


def test_low_confidence_issue_penalises_less():
    strong = [{"severity": "warning", "confidence": 1.0, "title": "a"}]
    weak = [{"severity": "warning", "confidence": 0.3, "title": "a"}]
    assert score_check(weak)["score"] > score_check(strong)["score"]


# --------------------------------------------------------------------------
# rule packs
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(PACK_DIR.glob("*.json")), ids=lambda p: p.name)
def test_bundled_rulepacks_are_valid(path):
    errors = validate_pack(json.loads(path.read_text(encoding="utf-8")))
    assert errors == [], f"{path.name}: {errors}"


def test_bundled_rulepacks_are_marked_unverified():
    """Draft packs must stay flagged until real casework verifies them (§9)."""
    for path in PACK_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("unverified") is True, path.name


def test_validator_rejects_unknown_document_type():
    pack = _pack([], documents=[{"key": "not_a_real_type", "required": True,
                                 "fix": "x"}])
    assert any("unknown document type" in e for e in validate_pack(pack))


def test_validator_rejects_pack_with_no_required_documents():
    pack = _pack([], documents=[{"key": "passport", "required": False}])
    assert any("never report a missing document" in e for e in validate_pack(pack))


def test_validator_rejects_unknown_rule_type():
    pack = _pack([{"id": "x", "type": "does_not_exist", "params": {}}])
    assert any("unknown rule type" in e for e in validate_pack(pack))


def test_validator_rejects_bad_photo_ratio():
    pack = _pack([{"id": "p", "type": "photo_spec",
                   "params": {"face_height_ratio": [0.9, 0.5]}}])
    assert any("face_height_ratio" in e for e in validate_pack(pack))
