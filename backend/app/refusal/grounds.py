"""The standard Schengen refusal grounds, and what to do about each one.

Why this file exists: when a Schengen visa is refused, the consulate must hand
back the standard form from Annex VI of the Visa Code (Regulation 810/2009).
It is the same form in all 29 states, and the officer simply ticks numbered
boxes. That makes a refusal letter *machine-decodable* — the reason is a
number, not free prose.

Applicants receive this form and mostly cannot read it. "Ground 3" means
nothing to someone who has just lost their fee. Decoding it into "your funds
evidence was not accepted; here is what to change before you reapply" is the
gap this module fills.

Each ground carries:

* the official wording, so the user can match it against their own letter;
* what it actually means, in plain language;
* whether reapplying or appealing is the sensible move;
* ``rule_ids`` — the checks in our own rule packs that speak to this ground.
  That link is what lets a decoded refusal be turned back into a targeted
  re-check, and it is also how real refusals tell us whether our rule packs
  are any good.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SOURCE = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A32009R0810"


@dataclass(frozen=True)
class Ground:
    number: int
    code: str
    official: str          # wording as printed on the form
    plain: str             # what it means to the applicant
    category: str          # document | purpose | funds | stay | security | insurance | credibility
    fixable: bool          # can a better-prepared reapplication realistically fix it?
    action: str            # what to do next
    rule_ids: tuple[str, ...] = field(default=())
    appeal_note: str = ""


# The eleven numbered grounds from the Annex VI standard form. Wording is
# reproduced closely from the Visa Code; confirm against the applicant's own
# letter, since member states print it in their own language.
GROUNDS: tuple[Ground, ...] = (
    Ground(
        number=1,
        code="false_document",
        official="A false, counterfeit or forged travel document was presented.",
        plain=(
            "The consulate believes the passport or another travel document you "
            "presented was not genuine."
        ),
        category="document",
        fixable=False,
        action=(
            "This is the most serious ground on the form and is not a paperwork "
            "problem you can fix by reapplying. If your documents are genuine, this "
            "is a factual error and you should appeal in writing within the deadline "
            "on your letter, with evidence from the issuing authority. Take legal "
            "advice before reapplying."
        ),
        appeal_note="Appeal rather than reapply. Reapplying does not answer the allegation.",
    ),
    Ground(
        number=2,
        code="purpose_not_justified",
        official=(
            "Justification for the purpose and conditions of the intended stay was "
            "not provided."
        ),
        plain=(
            "The officer could not tell, from your documents, why you were going or "
            "what you would actually do there."
        ),
        category="purpose",
        fixable=True,
        action=(
            "Reapply with a clear itinerary and a cover letter that states the "
            "purpose plainly, plus confirmed accommodation and a round-trip "
            "reservation that match those dates exactly."
        ),
        rule_ids=(
            "doc.cover_letter", "doc.hotel_booking", "doc.flight_ticket",
            "doc.invitation_letter", "letter.cover_purpose",
            "itinerary.accommodation_covers_stay",
        ),
    ),
    Ground(
        number=3,
        code="insufficient_means",
        official=(
            "You have not provided proof of sufficient means of subsistence for the "
            "duration of the intended stay or for the return to the country of origin "
            "or residence, or you are not in a position to acquire such means lawfully."
        ),
        plain=(
            "Your money evidence was not accepted — either the balance was too low "
            "for the trip, or the officer could not see where it came from."
        ),
        category="funds",
        fixable=True,
        action=(
            "Reapply with a statement covering the full period your destination "
            "expects, a balance comfortably above the published daily amount for "
            "your trip length, and documentary proof of the origin of any large "
            "credit. If someone else is funding you, add a sponsorship letter with "
            "their own statements."
        ),
        rule_ids=(
            "financial.sufficiency", "financial.history", "financial.recency",
            "financial.sudden_deposit", "doc.bank_statement", "profile.income_proof",
        ),
    ),
    Ground(
        number=4,
        code="already_stayed_90",
        official=(
            "You have already stayed for 90 days during the current 180-day period on "
            "the territory of the Member States on the basis of a uniform visa or a "
            "visa with limited territorial validity."
        ),
        plain=(
            "Their records show you have already used your full short-stay allowance "
            "in the current rolling period."
        ),
        category="stay",
        fixable=True,
        action=(
            "This is an arithmetic question, not a document one. Recalculate your "
            "days across the last 180 days and apply for dates that fall outside the "
            "used allowance. If your calculation differs from theirs, appeal with "
            "your entry and exit stamps as evidence."
        ),
        appeal_note="Worth appealing if you can show their day count is wrong.",
    ),
    Ground(
        number=5,
        code="sis_alert",
        official=(
            "An alert has been issued in the Schengen Information System (SIS) for the "
            "purpose of refusing entry."
        ),
        plain=(
            "A Schengen state has entered an alert against you in the shared system."
        ),
        category="security",
        fixable=False,
        action=(
            "No document change will clear this. You have a right to ask which state "
            "entered the alert and to request correction or deletion of the data. "
            "Take legal advice — this is a data and rights question, not a paperwork one."
        ),
        appeal_note="Seek legal advice. Reapplying without clearing the alert will fail again.",
    ),
    Ground(
        number=6,
        code="public_policy_threat",
        official=(
            "One or more Member States consider you to be a threat to public policy, "
            "internal security, public health or the international relations of one or "
            "more of the Member States."
        ),
        plain=(
            "A member state raised an objection on security or public-policy grounds."
        ),
        category="security",
        fixable=False,
        action=(
            "This is not a documents problem. Take legal advice before doing anything "
            "else; reasons are often not disclosed in detail and the route forward is "
            "usually a formal appeal."
        ),
        appeal_note="Legal advice recommended.",
    ),
    Ground(
        number=7,
        code="no_insurance",
        official=(
            "Proof of holding adequate and valid travel medical insurance was not "
            "provided."
        ),
        plain=(
            "Your insurance was missing, or it did not meet the required cover, dates "
            "or territory."
        ),
        category="insurance",
        fixable=True,
        action=(
            "This is the most mechanically fixable ground on the form. Buy a policy "
            "with at least EUR 30,000 of medical cover, valid in all Schengen states, "
            "covering every day from departure to return, and explicitly stating "
            "repatriation for medical reasons and of remains."
        ),
        rule_ids=(
            "doc.travel_insurance", "insurance.coverage", "insurance.dates",
            "insurance.repatriation",
        ),
    ),
    Ground(
        number=8,
        code="info_not_reliable",
        official=(
            "The information submitted regarding the justification for the purpose and "
            "conditions of the intended stay was not reliable."
        ),
        plain=(
            "The officer did not believe the account your documents told — usually "
            "because parts of it contradicted each other."
        ),
        category="credibility",
        fixable=True,
        action=(
            "Contradictions between documents are the usual cause: dates that do not "
            "line up, a name spelled differently, an invitation that disagrees with "
            "the hotel booking. Rebuild the file so every document tells the identical "
            "story, then reapply."
        ),
        rule_ids=(
            "consistency.name", "consistency.dob", "consistency.passport_number",
            "itinerary.accommodation_covers_stay", "letter.invitation_completeness",
            "letter.employment_completeness",
        ),
    ),
    Ground(
        number=9,
        code="doubts_document_authenticity",
        official=(
            "There are reasonable doubts as to the authenticity of the supporting "
            "documents submitted by you or the veracity of their contents."
        ),
        plain=(
            "The officer suspected one or more of your supporting documents was not "
            "genuine, or that its contents were not true."
        ),
        category="credibility",
        fixable=True,
        action=(
            "Reapply with documents that can be independently verified: bank "
            "statements stamped and signed by the bank, employment letters on "
            "letterhead with a named contact and a working phone number, bookings "
            "with confirmation numbers the consulate can check. Avoid anything a "
            "third party cannot confirm."
        ),
        rule_ids=("doc.bank_statement", "doc.employment_letter", "employment.letter_age"),
    ),
    Ground(
        number=10,
        code="doubts_statements",
        official=(
            "There are reasonable doubts as to the reliability of the statements made "
            "by you regarding your intention to leave, or as to the intention to leave "
            "the territory of the Member States before the expiry of the visa."
        ),
        plain=(
            "The officer was not convinced you would return home before the visa "
            "expired. This is the hardest ground for applicants from high-refusal "
            "countries, and the most common."
        ),
        category="credibility",
        fixable=True,
        action=(
            "You need concrete, documented ties rather than statements of intent. "
            "Employment with dated approved leave and an expected return-to-work date; "
            "a business with registration and filed tax returns; property; dependants "
            "who stay behind; and any record of previous compliant travel."
        ),
        rule_ids=(
            "doc.employment_letter", "doc.property_document", "doc.previous_visa",
            "letter.cover_ties", "letter.employment_return",
            "letter.cover_genuine_visitor", "profile.income_proof",
        ),
    ),
    Ground(
        number=11,
        code="revocation_requested",
        official=(
            "Revocation of the visa was requested by the visa holder.",
        )[0],
        plain="The visa was revoked at the holder's own request.",
        category="stay",
        fixable=True,
        action="No action needed unless this was recorded in error.",
    ),
)

BY_NUMBER = {g.number: g for g in GROUNDS}
BY_CODE = {g.code: g for g in GROUNDS}

# Grounds that no amount of better paperwork will fix. Saying so plainly is
# kinder than selling someone a re-check that cannot help them.
NOT_PAPERWORK = tuple(g.code for g in GROUNDS if not g.fixable)


def ground(ref: int | str) -> Ground | None:
    if isinstance(ref, int):
        return BY_NUMBER.get(ref)
    key = str(ref).strip().lower()
    if key.isdigit():
        return BY_NUMBER.get(int(key))
    return BY_CODE.get(key)


def rules_for(codes) -> set[str]:
    """Every rule id implicated by a set of refusal grounds."""
    out: set[str] = set()
    for code in codes or ():
        g = ground(code)
        if g:
            out.update(g.rule_ids)
    return out


def as_catalogue() -> list[dict]:
    """The full list, for the UI's manual ground picker."""
    return [
        {
            "number": g.number,
            "code": g.code,
            "official": g.official,
            "plain": g.plain,
            "category": g.category,
            "fixable": g.fixable,
            "action": g.action,
            "appeal_note": g.appeal_note,
            "rule_ids": list(g.rule_ids),
        }
        for g in GROUNDS
    ]
