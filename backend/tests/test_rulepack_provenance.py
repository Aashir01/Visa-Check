"""Tests for rule-pack provenance and per-destination thresholds.

Two properties matter here beyond "does it run":

* A finding must be able to say where its requirement comes from. Telling
  someone "you need EUR 30,000 of insurance" is very different depending on
  whether that is the EU Visa Code or our own opinion.
* Schengen funds thresholds are set per member state and range from EUR 34/day
  to EUR 122.10/day. Applying one "Schengen" number is wrong by a factor of
  three at the extremes.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.pipeline.rules_engine import CheckContext, DocView, RulesEngine
from app.rulepack_schema import AUTHORITIES, validate_pack

PACK_DIR = Path(__file__).resolve().parent.parent / "app" / "rulepacks"
PACKS = sorted(PACK_DIR.glob("*.json"))


def load(name: str) -> dict:
    return json.loads((PACK_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def schengen() -> dict:
    return load("schengen_short_stay_pk.json")


# --------------------------------------------------------------------------
# provenance in the packs
# --------------------------------------------------------------------------


@pytest.mark.parametrize("path", PACKS, ids=lambda p: p.name)
def test_packs_declare_provenance(path):
    pack = json.loads(path.read_text(encoding="utf-8"))
    prov = pack.get("provenance")
    assert prov, f"{path.name} must declare provenance"
    assert "researched_at" in prov
    assert prov.get("verified_against_casework") is False, (
        "packs must stay flagged as unverified until real casework confirms them"
    )
    assert prov.get("sources"), "provenance must cite the sources it was built from"


@pytest.mark.parametrize("path", PACKS, ids=lambda p: p.name)
def test_every_rule_declares_an_authority(path):
    pack = json.loads(path.read_text(encoding="utf-8"))
    missing = [r["id"] for r in pack.get("rules", []) if not r.get("authority")]
    assert not missing, f"{path.name}: rules without an authority: {missing}"


@pytest.mark.parametrize("path", PACKS, ids=lambda p: p.name)
def test_official_claims_cite_a_source(path):
    """Anything presented as law or a state figure must say where it is written."""
    pack = json.loads(path.read_text(encoding="utf-8"))
    offenders = []
    for item in list(pack.get("rules", [])) + list(pack.get("documents", [])):
        if item.get("authority") in ("law", "member_state") and not item.get("sources"):
            offenders.append(item.get("id") or item.get("key"))
    assert not offenders, f"{path.name}: uncited official claims: {offenders}"


@pytest.mark.parametrize("path", PACKS, ids=lambda p: p.name)
def test_authorities_are_from_the_known_set(path):
    pack = json.loads(path.read_text(encoding="utf-8"))
    for item in list(pack.get("rules", [])) + list(pack.get("documents", [])):
        authority = item.get("authority")
        if authority is not None:
            assert authority in AUTHORITIES, f"{path.name}: bad authority {authority!r}"


def test_validator_rejects_an_uncited_legal_claim():
    pack = {
        "version": "t", "title": "t", "currency": "EUR",
        "documents": [{"key": "passport", "required": True, "fix": "x"}],
        "rules": [{
            "id": "r", "type": "passport_validity", "authority": "law",
            "params": {"min_days_after_return": 90},
        }],
    }
    errors = validate_pack(pack)
    assert any("requires at least one entry in 'sources'" in e for e in errors)


def test_validator_rejects_an_unknown_authority():
    pack = {
        "version": "t", "title": "t", "currency": "EUR",
        "documents": [{"key": "passport", "required": True, "fix": "x"}],
        "rules": [{
            "id": "r", "type": "passport_validity", "authority": "vibes",
            "params": {"min_days_after_return": 90},
        }],
    }
    assert any("authority must be one of" in e for e in validate_pack(pack))


# --------------------------------------------------------------------------
# provenance reaches the findings
# --------------------------------------------------------------------------


def _empty_ctx(pack: dict, **kw) -> CheckContext:
    start = date.today() + timedelta(days=40)
    return CheckContext(
        pack=pack, profile="employed", documents=kw.pop("documents", []),
        travel_start=start, travel_end=start + timedelta(days=9), **kw,
    )


def test_missing_document_finding_carries_its_authority(schengen):
    issues, _, _ = RulesEngine(schengen).evaluate(_empty_ctx(schengen))
    insurance = next(i for i in issues if i["rule_id"] == "doc.travel_insurance")
    assert insurance["authority"] == "law"
    assert any("eur-lex" in s for s in insurance["sources"])


def test_heuristic_findings_are_labelled_as_such():
    """A UK funds finding must not masquerade as a legal requirement."""
    pack = load("uk_visitor_pk.json")
    docs = [DocView(id="1", doc_type="bank_statement", filename="b.pdf",
                    fields={"closing_balance": 10_000, "currency": "PKR"})]
    issues, _, _ = RulesEngine(pack).evaluate(_empty_ctx(pack, documents=docs))
    funds = next(i for i in issues if i["rule_id"] == "financial.sufficiency")
    assert funds["authority"] == "heuristic"


def test_every_finding_exposes_the_provenance_fields(schengen):
    issues, _, _ = RulesEngine(schengen).evaluate(_empty_ctx(schengen))
    assert issues
    for issue in issues:
        assert "authority" in issue
        assert isinstance(issue["sources"], list)


# --------------------------------------------------------------------------
# per-destination funds thresholds
# --------------------------------------------------------------------------


def _funds_issue(pack: dict, pkr: float, destination: str | None):
    docs = [DocView(id="1", doc_type="bank_statement", filename="b.pdf",
                    fields={"closing_balance": pkr, "currency": "PKR"})]
    ctx = _empty_ctx(pack, documents=docs, destination_country=destination)
    issues, _, _ = RulesEngine(pack).evaluate(ctx)
    return next((i for i in issues if i["rule_id"] == "financial.sufficiency"), None)


def test_the_same_balance_passes_cheap_states_and_fails_expensive_ones(schengen):
    """EUR ~794 for 10 days clears the Netherlands and fails Spain."""
    balance = 250_000  # PKR, ~EUR 794 at the pack's indicative rate
    assert _funds_issue(schengen, balance, "NL") is None
    assert _funds_issue(schengen, balance, "DE") is None
    assert _funds_issue(schengen, balance, "FR") is None
    assert _funds_issue(schengen, balance, "ES") is not None
    assert _funds_issue(schengen, balance, "IT") is not None


def test_a_healthy_balance_clears_every_destination(schengen):
    for country in ("NL", "DE", "GR", "FR", "IT", "ES"):
        assert _funds_issue(schengen, 500_000, country) is None, country


def test_unknown_destination_falls_back_to_the_pack_default(schengen):
    """An unrecognised code must not silently drop the threshold to zero."""
    assert _funds_issue(schengen, 250_000, "ZZ") is not None
    assert _funds_issue(schengen, 250_000, None) is not None  # default is ES


def test_the_finding_names_the_member_state(schengen):
    issue = _funds_issue(schengen, 250_000, "ES")
    assert "ES" in issue["detail"]


def test_single_destination_corridors_ignore_the_table():
    """UK and Saudi have no per_destination map; a destination must not break them."""
    pack = load("uk_visitor_pk.json")
    docs = [DocView(id="1", doc_type="bank_statement", filename="b.pdf",
                    fields={"closing_balance": 10_000, "currency": "PKR"})]
    ctx = _empty_ctx(pack, documents=docs, destination_country="ES")
    issues, _, _ = RulesEngine(pack).evaluate(ctx)
    assert any(i["rule_id"] == "financial.sufficiency" for i in issues)


# --------------------------------------------------------------------------
# corrections this research produced
# --------------------------------------------------------------------------


def test_spain_amount_matches_the_smi_formula(schengen):
    """Spain sets 10% of gross SMI per day, floored at 90% of SMI (2026: EUR 1,221)."""
    params = next(r for r in schengen["rules"] if r["id"] == "financial.sufficiency")["params"]
    spain = params["per_destination"]["ES"]
    smi_2026 = 1221.0
    assert spain["per_day_amount"] == pytest.approx(smi_2026 * 0.10, abs=0.01)
    assert spain["minimum_total"] == pytest.approx(smi_2026 * 0.90, abs=0.01)


def test_uk_funds_floor_is_calibrated_not_doubled():
    """The old GBP 1,500 floor was ~2x the practical figure practitioners cite."""
    pack = load("uk_visitor_pk.json")
    params = next(r for r in pack["rules"] if r["id"] == "financial.sufficiency")["params"]
    assert params["minimum_total"] <= 900


def test_uk_does_not_require_a_tb_certificate_for_short_visits():
    """A TB test is only needed for stays over 6 months; requiring it would be wrong."""
    pack = load("uk_visitor_pk.json")
    tb = next(d for d in pack["documents"] if "TB test" in (d.get("label") or ""))
    assert tb.get("required") is False


def test_saudi_mahram_proof_is_not_blocking():
    """Women of all ages may now perform Umrah without a mahram in a licensed group."""
    pack = load("saudi_umrah_pk.json")
    mahram = next(d for d in pack["documents"] if d["key"] == "mahram_proof")
    assert mahram.get("required") is False


def test_saudi_requires_the_acwy_certificate():
    pack = load("saudi_umrah_pk.json")
    vac = next(d for d in pack["documents"] if d["key"] == "vaccination_certificate")
    assert vac["required"] is True
    assert vac["severity"] == "critical"


def test_schengen_insurance_minimum_is_the_visa_code_figure(schengen):
    rule = next(r for r in schengen["rules"] if r["id"] == "insurance.coverage")
    assert rule["params"]["min"] == 30000
    assert rule["authority"] == "law"
