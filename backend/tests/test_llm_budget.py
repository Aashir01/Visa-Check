"""Tests for LLM cost accounting, budget enforcement and response parsing.

§9 lists "LLM cost per check exceeds price" as a live risk. The budget is
therefore enforced, not merely reported, and these tests pin that behaviour:
once a check has spent its allowance, further calls are refused and the
pipeline degrades to deterministic findings.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.pipeline.llm import LlmCall, LlmUsage, extract_json, price
from app.pipeline.qualitative import review


# --------------------------------------------------------------------------
# pricing
# --------------------------------------------------------------------------


def test_price_uses_configured_rates():
    expected = (
        1_000_000 / 1_000_000 * settings.llm_price_in_per_mtok
        + 1_000_000 / 1_000_000 * settings.llm_price_out_per_mtok
    )
    assert price(1_000_000, 1_000_000) == pytest.approx(expected)


def test_price_of_nothing_is_zero():
    assert price(0, 0) == 0.0


def test_usage_totals_across_calls():
    usage = LlmUsage()
    usage.calls.append(LlmCall("extraction", "m", 1000, 500, price(1000, 500)))
    usage.calls.append(LlmCall("qualitative", "m", 2000, 800, price(2000, 800)))
    assert usage.tokens_in == 3000
    assert usage.tokens_out == 1300
    assert usage.usd == pytest.approx(price(1000, 500) + price(2000, 800))


# --------------------------------------------------------------------------
# budget
# --------------------------------------------------------------------------


def test_budget_not_exhausted_when_cheap():
    usage = LlmUsage()
    usage.calls.append(LlmCall("extraction", "m", 100, 50, 0.001))
    assert usage.exhausted() is False
    assert usage.remaining() > 0


def test_budget_exhausted_stops_further_spend():
    usage = LlmUsage()
    usage.calls.append(
        LlmCall("extraction", "m", 0, 0, settings.llm_budget_usd_per_check + 0.01)
    )
    assert usage.exhausted() is True
    assert usage.remaining() == 0.0


# --------------------------------------------------------------------------
# response parsing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        '{"results": [{"id": "a"}]}',
        '```json\n{"results": [{"id": "a"}]}\n```',
        '```\n{"results": [{"id": "a"}]}\n```',
        'Here you go:\n{"results": [{"id": "a"}]}\nHope that helps.',
    ],
)
def test_extract_json_handles_model_formatting(raw):
    assert extract_json(raw) == {"results": [{"id": "a"}]}


def test_extract_json_returns_none_on_garbage():
    assert extract_json("no json at all") is None
    assert extract_json("") is None


# --------------------------------------------------------------------------
# qualitative review degrades safely
# --------------------------------------------------------------------------


class _StubLlm:
    """Stands in for LlmClient, returning a canned findings payload."""

    def __init__(self, payload, available=True):
        self.payload = payload
        self.available = available
        self.calls = 0

    def complete_json(self, **_kwargs):
        self.calls += 1
        return self.payload


class _Doc:
    def __init__(self, doc_type, text="some letter text"):
        self.id = "d1"
        self.doc_type = doc_type
        self.filename = "letter.pdf"
        self.text = text


PACK = {
    "llm_review": {
        "enabled": True,
        "targets": ["employment_letter"],
        "criteria": [
            {
                "id": "letter.completeness",
                "document": "employment_letter",
                "label": "Letter is missing details",
                "severity": "warning",
                "question": "Does it state salary?",
                "fix": "Ask for a new letter.",
            }
        ],
    }
}


def test_unavailable_llm_produces_no_findings():
    llm = _StubLlm(None, available=False)
    issues, passed = review(llm, PACK, [_Doc("employment_letter")])
    assert issues == [] and passed == []
    assert llm.calls == 0


def test_no_relevant_document_skips_the_call():
    llm = _StubLlm({"findings": []})
    issues, passed = review(llm, PACK, [_Doc("passport")])
    assert issues == [] and passed == []
    assert llm.calls == 0, "must not spend tokens when no target document is present"


def test_fail_finding_becomes_an_issue():
    llm = _StubLlm({
        "findings": [{
            "criterion_id": "letter.completeness",
            "document_id": "d1",
            "status": "fail",
            "detail": "The letter never states a salary.",
            "evidence": "employed since 2019",
            "confidence": 0.8,
        }]
    })
    issues, passed = review(llm, PACK, [_Doc("employment_letter")])
    assert len(issues) == 1
    assert issues[0]["severity"] == "warning"
    assert issues[0]["fix"] == "Ask for a new letter."
    assert issues[0]["evidence"][0]["value"] == "employed since 2019"
    assert passed == []


def test_pass_finding_becomes_a_passed_check():
    llm = _StubLlm({
        "findings": [{
            "criterion_id": "letter.completeness",
            "document_id": "d1",
            "status": "pass",
            "confidence": 0.9,
        }]
    })
    issues, passed = review(llm, PACK, [_Doc("employment_letter")])
    assert issues == []
    assert len(passed) == 1


def test_unclear_verdict_is_downgraded_to_info():
    llm = _StubLlm({
        "findings": [{
            "criterion_id": "letter.completeness",
            "document_id": "d1",
            "status": "unclear",
            "detail": "Could not tell from the text.",
            "confidence": 0.7,
        }]
    })
    issues, _ = review(llm, PACK, [_Doc("employment_letter")])
    assert issues[0]["severity"] == "info"


def test_low_confidence_failure_is_downgraded_to_info():
    llm = _StubLlm({
        "findings": [{
            "criterion_id": "letter.completeness",
            "document_id": "d1",
            "status": "fail",
            "detail": "Maybe missing.",
            "confidence": 0.2,
        }]
    })
    issues, _ = review(llm, PACK, [_Doc("employment_letter")])
    assert issues[0]["severity"] == "info"


def test_model_findings_never_read_as_certain():
    llm = _StubLlm({
        "findings": [{
            "criterion_id": "letter.completeness",
            "document_id": "d1",
            "status": "fail",
            "detail": "Definitely missing.",
            "confidence": 1.0,
        }]
    })
    issues, _ = review(llm, PACK, [_Doc("employment_letter")])
    assert issues[0]["confidence"] <= 0.8


def test_unknown_criterion_id_is_ignored():
    """A hallucinated criterion must not become a finding."""
    llm = _StubLlm({
        "findings": [{
            "criterion_id": "invented.criterion",
            "document_id": "d1",
            "status": "fail",
            "detail": "Something else entirely.",
            "confidence": 0.9,
        }]
    })
    issues, passed = review(llm, PACK, [_Doc("employment_letter")])
    assert issues == [] and passed == []


def test_malformed_response_is_survivable():
    for payload in (None, [], {"findings": None}, {"wrong_key": []}):
        issues, passed = review(_StubLlm(payload), PACK, [_Doc("employment_letter")])
        assert issues == [] and passed == []


def test_disabled_review_makes_no_call():
    pack = {"llm_review": {**PACK["llm_review"], "enabled": False}}
    llm = _StubLlm({"findings": []})
    review(llm, pack, [_Doc("employment_letter")])
    assert llm.calls == 0
