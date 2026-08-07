"""The document taxonomy shared by classification, rule packs and the UI."""

from __future__ import annotations

DOC_TYPES: dict[str, str] = {
    "passport": "Passport",
    "national_id": "National ID card",
    "photo": "Passport photograph",
    "bank_statement": "Bank statement",
    "bank_letter": "Bank balance certificate / letter",
    "employment_letter": "Employment letter / NOC",
    "salary_slip": "Salary slip",
    "business_registration": "Business registration / NTN",
    "tax_return": "Tax return",
    "student_enrollment": "Student enrolment letter",
    "pension_statement": "Pension statement",
    "invitation_letter": "Invitation letter",
    "sponsor_letter": "Sponsorship letter / affidavit of support",
    "hotel_booking": "Hotel / accommodation booking",
    "flight_ticket": "Flight reservation",
    "travel_insurance": "Travel medical insurance",
    "cover_letter": "Cover letter",
    "application_form": "Visa application form",
    "previous_visa": "Previous visa / travel history",
    "marriage_certificate": "Marriage certificate",
    "birth_certificate": "Birth certificate",
    "property_document": "Property document",
    "police_certificate": "Police clearance certificate",
    "vaccination_certificate": "Vaccination certificate",
    "mahram_proof": "Mahram relationship proof",
    "unknown": "Unrecognised document",
}


def label_for(key: str | None) -> str:
    if not key:
        return DOC_TYPES["unknown"]
    return DOC_TYPES.get(key, key.replace("_", " ").title())
