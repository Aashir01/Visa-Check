"""Tests for refusal decoding, recovery plans, re-check diffs and timelines.

The decoder's job is to be right or silent. A wrongly decoded refusal sends
someone to reapply against the wrong problem, or to appeal when they should
have reapplied — both cost money and time they have already lost once.
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.pipeline.diff import diff_against_refusal, diff_checks
from app.pipeline.timeline import build_timeline, summarise
from app.refusal import (
    as_catalogue,
    build,
    decode,
    decode_text,
    from_manual,
    ground,
    rules_for,
)
from app.refusal.plan import appeal_guidance

TICKED = """
Consulate General of Spain in Karachi
Date of decision: 12/07/2026
DECISION ON THE APPLICATION FOR A SCHENGEN VISA
[x] 3. You have not provided proof of sufficient means of subsistence for the
duration of the intended stay or for the return to the country of origin.
[x] 7. Proof of holding adequate and valid travel medical insurance was not provided.
"""

PROSE = """
The consulate has refused your application. There are reasonable doubts as to the
reliability of the statements made by you regarding your intention to leave the
territory of the Member States before the expiry of the visa applied for.
"""


# --------------------------------------------------------------------------
# catalogue
# --------------------------------------------------------------------------


def test_catalogue_has_all_eleven_grounds():
    cat = as_catalogue()
    assert len(cat) == 11
    assert [g["number"] for g in cat] == list(range(1, 12))


def test_grounds_are_resolvable_by_number_and_code():
    assert ground(3).code == "insufficient_means"
    assert ground("3").code == "insufficient_means"
    assert ground("no_insurance").number == 7
    assert ground("nonsense") is None


def test_security_grounds_are_marked_unfixable():
    """Paperwork cannot answer a SIS alert or a forgery allegation."""
    for code in ("false_document", "sis_alert", "public_policy_threat"):
        assert ground(code).fixable is False


def test_fixable_grounds_map_to_real_rules():
    for g in (ground(c) for c in ("insufficient_means", "no_insurance",
                                  "purpose_not_justified", "doubts_statements")):
        assert g.rule_ids, f"{g.code} should implicate rules"


def test_rules_for_collects_across_grounds():
    rules = rules_for(["no_insurance", "insufficient_means"])
    assert "insurance.coverage" in rules
    assert "financial.sufficiency" in rules


# --------------------------------------------------------------------------
# deterministic decoding
# --------------------------------------------------------------------------


def test_ticked_form_decodes_with_high_confidence():
    result = decode_text(TICKED)
    assert result.method == "deterministic"
    assert set(result.codes) == {"insufficient_means", "no_insurance"}
    assert result.confidence >= 0.9


def test_ticked_form_extracts_the_consulate():
    assert "Spain" in (decode_text(TICKED).consulate or "")


def test_prose_letter_decodes_without_tick_marks():
    """Some states print the reasons as prose; the wording still identifies them."""
    result = decode_text(PROSE)
    assert result.codes == ["doubts_statements"]


def test_unrecognisable_text_decodes_to_nothing():
    result = decode("Dear applicant, your application was unsuccessful. Regards.")
    assert result.grounds == []
    assert result.notes, "an undecodable letter must explain itself"


def test_empty_input_is_safe():
    assert decode_text("").grounds == []
    assert decode_text("   ").grounds == []


def test_decoder_does_not_invent_grounds_from_context():
    """Mentioning money must not by itself produce a funds refusal."""
    text = "Your application included bank statements and an insurance policy. Refused."
    assert decode_text(text).codes == []


def test_manual_selection_is_fully_confident():
    result = from_manual(["no_insurance", "insufficient_means"])
    assert result.method == "manual"
    assert result.confidence == 1.0
    assert len(result.grounds) == 2


def test_manual_selection_ignores_unknown_codes():
    assert from_manual(["no_insurance", "not_a_ground"]).codes == ["no_insurance"]


# --------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------


def test_fixable_refusal_offers_a_recheck():
    plan = build(decode_text(TICKED))
    assert plan["verdict"] == "reapply"
    assert plan["can_recheck"] is True
    assert plan["fixable_count"] == 2


def test_blocking_ground_refuses_to_offer_a_recheck():
    """Selling a re-check against a SIS alert would be taking money for nothing."""
    plan = build(from_manual(["sis_alert"]))
    assert plan["verdict"] == "seek_advice"
    assert plan["can_recheck"] is False
    assert plan["blocking_count"] == 1


def test_one_blocking_ground_poisons_a_mixed_refusal():
    plan = build(from_manual(["no_insurance", "false_document"]))
    assert plan["can_recheck"] is False
    assert plan["verdict"] == "seek_advice"


def test_intention_to_leave_is_not_sold_as_an_easy_fix():
    plan = build(from_manual(["doubts_statements"]))
    assert plan["verdict"] == "reapply_hard"
    assert "ties" in plan["summary"].lower()


def test_blocking_grounds_are_ordered_first():
    plan = build(from_manual(["no_insurance", "sis_alert"]))
    assert plan["steps"][0]["ground_code"] == "sis_alert"


def test_undecoded_plan_asks_for_the_form():
    plan = build(decode("nothing useful here at all"))
    assert plan["verdict"] == "undecoded"
    assert plan["can_recheck"] is False


def test_plan_links_grounds_to_checklist_documents():
    pack = {
        "documents": [
            {"key": "travel_insurance", "label": "Travel medical insurance",
             "fix": "Buy a compliant policy.", "authority": "law"},
            {"key": "passport", "label": "Passport", "fix": "Upload it."},
        ],
        "rules": [{"id": "insurance.coverage", "title": "Cover too low",
                   "fix": "Get EUR 30,000.", "authority": "law"}],
    }
    plan = build(from_manual(["no_insurance"]), pack)
    step = plan["steps"][0]
    assert [d["key"] for d in step["documents"]] == ["travel_insurance"]
    assert [r["id"] for r in step["rules"]] == ["insurance.coverage"]


def test_appeal_guidance_appears_for_blocking_grounds():
    guidance = appeal_guidance(from_manual(["sis_alert"]))
    assert guidance["applicable"] is True
    assert "deadline" in guidance["general"].lower()


def test_appeal_guidance_absent_for_ordinary_grounds():
    assert appeal_guidance(from_manual(["no_insurance"]))["applicable"] is False


# --------------------------------------------------------------------------
# re-check diffs
# --------------------------------------------------------------------------


def _check(issues, score=50, cid="c1"):
    return SimpleNamespace(id=cid, issues=issues, risk_score=score)


def _issue(rule_id, severity="critical", title=None):
    return {"rule_id": rule_id, "severity": severity,
            "title": title or rule_id, "category": "x", "fix": "do it"}


def test_diff_separates_resolved_remaining_and_new():
    before = _check([_issue("a"), _issue("b")], score=40)
    after = _check([_issue("b"), _issue("c")], score=70)
    d = diff_checks(before, after)
    assert [r["rule_id"] for r in d["resolved"]] == ["a"]
    assert [r["rule_id"] for r in d["remaining"]] == ["b"]
    assert [r["rule_id"] for r in d["introduced"]] == ["c"]
    assert d["score_delta"] == 30


def test_diff_reports_a_clean_file():
    d = diff_checks(_check([_issue("a")], 40), _check([], 100))
    assert d["counts"]["resolved"] == 1
    assert "clear" in d["headline"].lower()


def test_diff_warns_while_a_critical_remains():
    d = diff_checks(_check([_issue("a")], 40), _check([_issue("a")], 45))
    assert "not ready" in d["headline"].lower()


def test_diff_flags_newly_introduced_issues():
    d = diff_checks(_check([], 100), _check([_issue("new", "warning")], 90))
    assert d["counts"]["introduced"] == 1
    assert "new" in d["headline"].lower()


def test_diff_handles_missing_scores():
    d = diff_checks(_check([], None), _check([], None))
    assert d["score_delta"] is None


# --------------------------------------------------------------------------
# diff against the refusal itself
# --------------------------------------------------------------------------


def test_refusal_ground_clears_when_its_rules_stop_firing():
    refusal = SimpleNamespace(id="r1", ground_codes=["no_insurance"])
    after = _check([_issue("something.else")])
    d = diff_against_refusal(refusal, after)
    assert d["grounds"][0]["cleared"] is True
    assert d["counts"]["cleared"] == 1


def test_refusal_ground_stays_open_while_its_rule_still_fires():
    """Adding insurance with the wrong dates must not read as fixed."""
    refusal = SimpleNamespace(id="r1", ground_codes=["no_insurance"])
    after = _check([_issue("insurance.dates")])
    d = diff_against_refusal(refusal, after)
    assert d["grounds"][0]["cleared"] is False
    assert d["grounds"][0]["still_open_rules"] == ["insurance.dates"]


def test_unfixable_ground_never_reports_as_cleared():
    refusal = SimpleNamespace(id="r1", ground_codes=["sis_alert"])
    d = diff_against_refusal(refusal, _check([]))
    assert d["grounds"][0]["cleared"] is False
    assert d["counts"]["blocking"] == 1


# --------------------------------------------------------------------------
# submission-date timeline
# --------------------------------------------------------------------------


class _Doc:
    def __init__(self, doc_type, fields):
        self.doc_type = doc_type
        self.fields = fields

    def get(self, k, default=None):
        return self.fields.get(k, default)


class _Ctx:
    def __init__(self, docs, submission):
        self._docs = docs
        self.submission_date = submission

    def first(self, doc_type):
        return next((d for d in self._docs if d.doc_type == doc_type), None)


PACK = {
    "rules": [
        {"id": "financial.recency", "type": "statement_recency",
         "params": {"document": "bank_statement", "field": "statement_date",
                    "max_age_days": 30}},
    ]
}


def test_statement_valid_today_but_expired_at_the_appointment():
    """The whole point: valid now, stale by the date that actually counts."""
    today = date.today()
    docs = [_Doc("bank_statement", {"statement_date": (today - timedelta(days=5)).isoformat()})]

    now = build_timeline(_Ctx(docs, today), PACK)
    assert now[0]["status"] == "ok"

    later = build_timeline(_Ctx(docs, today + timedelta(days=30)), PACK)
    assert later[0]["status"] == "expired"
    assert "too old" in later[0]["detail"]


def test_expiring_soon_is_distinguished_from_fine():
    today = date.today()
    docs = [_Doc("bank_statement", {"statement_date": (today - timedelta(days=25)).isoformat()})]
    tl = build_timeline(_Ctx(docs, today), PACK)
    assert tl[0]["status"] == "expiring"
    assert tl[0]["days_remaining"] == 5


def test_passport_expiry_appears_on_the_timeline():
    today = date.today()
    docs = [_Doc("passport", {"expiry_date": (today + timedelta(days=400)).isoformat()})]
    tl = build_timeline(_Ctx(docs, today), {})
    assert tl[0]["document_type"] == "passport"
    assert tl[0]["status"] == "ok"


def test_expired_passport_is_flagged():
    today = date.today()
    docs = [_Doc("passport", {"expiry_date": (today - timedelta(days=5)).isoformat()})]
    assert build_timeline(_Ctx(docs, today), {})[0]["status"] == "expired"


def test_timeline_is_ordered_by_what_expires_first():
    today = date.today()
    docs = [
        _Doc("passport", {"expiry_date": (today + timedelta(days=900)).isoformat()}),
        _Doc("travel_insurance", {"valid_to": (today + timedelta(days=30)).isoformat()}),
    ]
    tl = build_timeline(_Ctx(docs, today), {})
    assert tl[0]["document_type"] == "travel_insurance"


def test_documents_without_dates_are_omitted_not_guessed():
    tl = build_timeline(_Ctx([_Doc("passport", {})], date.today()), {})
    assert tl == []


def test_summarise_counts_and_finds_the_soonest():
    today = date.today()
    docs = [
        _Doc("passport", {"expiry_date": (today - timedelta(days=1)).isoformat()}),
        _Doc("travel_insurance", {"valid_to": (today + timedelta(days=3)).isoformat()}),
    ]
    s = summarise(build_timeline(_Ctx(docs, today), {}))
    assert s["expired"] == 1 and s["expiring"] == 1
    assert s["soonest"]["document_type"] == "passport"


# --------------------------------------------------------------------------
# the report card, aggregated
#
# The admin insights page is how a gap in the rules becomes visible. Two things
# have to stay true for it to be trustworthy: a ground nobody has graded yet
# must not look like a perfect score, and a ground with no rules behind it must
# be distinguishable from one whose rules simply failed to fire.
# --------------------------------------------------------------------------

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.admin import refusal_insights
from app.db import Base
from app.models import Refusal


@pytest.fixture
def insights_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path/'insights.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


def _refusal(db, *, codes, caught=(), missed=(), check_id="chk", status="decoded",
             method="deterministic"):
    row = Refusal(
        user_id="u1",
        check_id=check_id,
        status=status,
        method=method,
        ground_codes=list(codes),
        caught_by_check=[{"code": c, "number": 0, "rules": []} for c in caught],
        missed_by_check=[{"code": c, "number": 0, "rules": []} for c in missed],
    )
    db.add(row)
    db.commit()
    return row


def _by_code(result):
    return {g["code"]: g for g in result["grounds"]}


def test_catch_rate_counts_only_grounds_that_were_graded(insights_db):
    _refusal(insights_db, codes=["insufficient_means"], caught=["insufficient_means"])
    _refusal(insights_db, codes=["insufficient_means"], missed=["insufficient_means"])
    g = _by_code(refusal_insights(days=90, db=insights_db))["insufficient_means"]
    assert g["cited"] == 2 and g["caught"] == 1 and g["missed"] == 1
    assert g["catch_rate"] == 0.5


def test_an_ungraded_ground_has_no_catch_rate_rather_than_a_perfect_one(insights_db):
    """A refusal with no prior check cannot grade us. Silence is not a pass."""
    _refusal(insights_db, codes=["no_insurance"], check_id=None)
    g = _by_code(refusal_insights(days=90, db=insights_db))["no_insurance"]
    assert g["cited"] == 1
    assert g["catch_rate"] is None
    assert g["caught"] == 0 and g["missed"] == 0


def test_grounds_are_ordered_worst_catch_rate_first(insights_db):
    _refusal(insights_db, codes=["insufficient_means"], caught=["insufficient_means"])
    _refusal(insights_db, codes=["no_insurance"], missed=["no_insurance"])
    order = [g["code"] for g in refusal_insights(days=90, db=insights_db)["grounds"]]
    assert order.index("no_insurance") < order.index("insufficient_means")


def test_a_ground_with_no_rules_behind_it_is_flagged(insights_db):
    """No rule can ever catch this one — a different problem from a rule that
    exists and misses, and the fix is different too."""
    _refusal(insights_db, codes=["false_document"], missed=["false_document"])
    g = _by_code(refusal_insights(days=90, db=insights_db))["false_document"]
    assert g["has_rules"] is False


def test_gaps_lists_only_grounds_we_actually_missed(insights_db):
    _refusal(insights_db, codes=["insufficient_means"], caught=["insufficient_means"])
    _refusal(insights_db, codes=["no_insurance"], missed=["no_insurance"])
    result = refusal_insights(days=90, db=insights_db)
    assert [g["code"] for g in result["gaps"]] == ["no_insurance"]


def test_deterministic_share_reports_how_much_ran_without_a_model(insights_db):
    _refusal(insights_db, codes=["insufficient_means"], method="deterministic")
    _refusal(insights_db, codes=["insufficient_means"], method="deterministic")
    _refusal(insights_db, codes=["doubts_statements"], method="llm")
    result = refusal_insights(days=90, db=insights_db)
    assert result["deterministic_share"] == round(2 / 3, 3)


def test_an_undecoded_refusal_is_counted_but_grades_nothing(insights_db):
    _refusal(insights_db, codes=[], status="undecoded", method="none")
    result = refusal_insights(days=90, db=insights_db)
    assert result["total"] == 1 and result["decoded"] == 0 and result["undecoded"] == 1
    assert result["grounds"] == []
