#!/usr/bin/env python3
"""Generate synthetic document bundles for testing the pipeline.

These are deliberately *not* realistic-looking forgeries — they are plain
text-layer PDFs carrying the same field vocabulary real documents use, which
is what the extractors key on. They let you exercise the whole pipeline
without putting a real applicant's passport on disk.

    python tests/make_fixtures.py --out /tmp/bundle --case clean
    python tests/make_fixtures.py --out /tmp/bad --case problems
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

TODAY = date.today()


def _mrz_check(payload: str) -> str:
    weights = (7, 3, 1)

    def val(ch: str) -> int:
        if ch.isdigit():
            return int(ch)
        if ch == "<":
            return 0
        return ord(ch.upper()) - 55

    return str(sum(val(c) * weights[i % 3] for i, c in enumerate(payload)) % 10)


def build_mrz(passport_no: str, surname: str, given: str, dob: date,
              expiry: date, sex: str = "M", country: str = "PAK") -> tuple[str, str]:
    name_field = f"{surname}<<{given.replace(' ', '<')}".ljust(39, "<")[:39]
    line1 = f"P<{country}{name_field}"

    doc = passport_no.ljust(9, "<")[:9]
    dob_s = dob.strftime("%y%m%d")
    exp_s = expiry.strftime("%y%m%d")
    personal = "<" * 14

    composite = (doc + _mrz_check(doc) + dob_s + _mrz_check(dob_s) + exp_s
                 + _mrz_check(exp_s) + personal + _mrz_check(personal))
    line2 = (
        f"{doc}{_mrz_check(doc)}{country}{dob_s}{_mrz_check(dob_s)}{sex}"
        f"{exp_s}{_mrz_check(exp_s)}{personal}{_mrz_check(personal)}"
        f"{_mrz_check(composite)}"
    )
    return line1, line2[:44]


def write_pdf(path: Path, lines: list[str], *, mono_from: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    _, height = A4
    y = height - 60
    for i, line in enumerate(lines):
        if mono_from is not None and i >= mono_from:
            c.setFont("Courier", 10.5)
        elif line.isupper() and len(line) < 60:
            c.setFont("Helvetica-Bold", 12)
        else:
            c.setFont("Helvetica", 10)
        c.drawString(50, y, line)
        y -= 15
        if y < 60:
            c.showPage()
            y = height - 60
    c.save()


def make_photo(path: Path, *, width=413, height=531, background=(245, 245, 245),
               blur=False, greyscale=False, face=True) -> None:
    """A crude but face-detectable portrait: oval head on a plain ground."""
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.new("RGB", (width, height), background)
    d = ImageDraw.Draw(img)

    if face:
        # Head occupies ~72% of height, matching a compliant photo.
        head_h = int(height * 0.72)
        head_w = int(head_h * 0.72)
        cx, top = width // 2, int(height * 0.13)
        d.ellipse([cx - head_w // 2, top, cx + head_w // 2, top + head_h],
                  fill=(226, 190, 160))
        eye_y = top + int(head_h * 0.42)
        eye_dx = int(head_w * 0.20)
        for sign in (-1, 1):
            ex = cx + sign * eye_dx
            d.ellipse([ex - 13, eye_y - 8, ex + 13, eye_y + 8], fill=(255, 255, 255))
            d.ellipse([ex - 6, eye_y - 6, ex + 6, eye_y + 6], fill=(45, 35, 30))
            d.line([ex - 17, eye_y - 19, ex + 17, eye_y - 21], fill=(70, 50, 40), width=4)
        d.line([cx, eye_y + 8, cx, eye_y + int(head_h * 0.16)], fill=(190, 150, 125), width=4)
        mouth_y = top + int(head_h * 0.74)
        d.arc([cx - 34, mouth_y - 16, cx + 34, mouth_y + 16], 200, 340,
              fill=(150, 90, 85), width=5)
        d.ellipse([cx - head_w // 2 - 8, top + int(head_h * 0.30),
                   cx - head_w // 2 + 8, top + int(head_h * 0.55)], fill=(219, 182, 152))
        d.ellipse([cx + head_w // 2 - 8, top + int(head_h * 0.30),
                   cx + head_w // 2 + 8, top + int(head_h * 0.55)], fill=(219, 182, 152))

    if greyscale:
        img = img.convert("L").convert("RGB")
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(5))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, dpi=(300, 300))


# --------------------------------------------------------------------------


def bundle_clean(out: Path) -> dict:
    """A bundle that should score well: consistent, sufficient, in date."""
    dep = TODAY + timedelta(days=45)
    ret = dep + timedelta(days=10)
    name_sur, name_giv = "KHAN", "AHMED RAZA"
    full = f"{name_giv} {name_sur}"
    passport_no = "AB1234567"
    dob = date(1990, 4, 12)
    expiry = TODAY + timedelta(days=1500)

    l1, l2 = build_mrz(passport_no, name_sur, name_giv, dob, expiry)
    write_pdf(out / "passport.pdf", [
        "ISLAMIC REPUBLIC OF PAKISTAN", "PASSPORT",
        f"Passport No: {passport_no}",
        f"Name: {name_giv}", f"Surname: {name_sur}",
        "Nationality: PAKISTANI",
        f"Date of Birth: {dob.strftime('%d/%m/%Y')}",
        "Place of Birth: KARACHI",
        f"Date of Issue: {(TODAY - timedelta(days=900)).strftime('%d/%m/%Y')}",
        f"Date of Expiry: {expiry.strftime('%d/%m/%Y')}",
        "Machine readable zone:", l1, l2,
    ], mono_from=11)

    rows = []
    balance = 1_250_000
    for i in range(24):
        d = TODAY - timedelta(days=185 - i * 7)
        amount = 18_000 + (i % 5) * 2_400
        balance += amount
        rows.append(f"{d.strftime('%d/%m/%Y')}   Salary credit      {amount:,.2f}   "
                    f"{balance:,.2f}")

    write_pdf(out / "bank_statement.pdf", [
        "HABIB BANK LIMITED", "STATEMENT OF ACCOUNT",
        f"Account Title: {full}", "Account Number: 0123456789012",
        "Currency: PKR",
        f"Statement Period: {(TODAY - timedelta(days=185)).strftime('%d/%m/%Y')} "
        f"to {(TODAY - timedelta(days=3)).strftime('%d/%m/%Y')}",
        f"Opening Balance: 1,250,000.00",
        "Transaction Date  Details            Credit        Balance",
        *rows,
        f"Closing Balance: {balance:,.2f}",
    ])

    write_pdf(out / "insurance.pdf", [
        "TRAVEL MEDICAL INSURANCE CERTIFICATE",
        "Insurer: EFU General Insurance Limited",
        "Policy Number: SCH-2026-889231",
        f"Insured Person: {full}",
        f"Passport No: {passport_no}",
        "Area of Validity: All Schengen States",
        "Sum Insured: EUR 30,000",
        "Coverage: Medical expenses, emergency hospitalisation and repatriation",
        "This policy includes repatriation for medical reasons and repatriation of remains.",
        f"Valid from {dep.strftime('%d/%m/%Y')} to {ret.strftime('%d/%m/%Y')}",
    ])

    write_pdf(out / "flight.pdf", [
        "ELECTRONIC TICKET RECEIPT", "E-TICKET",
        "Airline: Turkish Airlines", "Booking Reference: 4XKP2Q",
        f"Passenger Name: {full}",
        "Flight Number: TK709",
        f"Departure: {dep.strftime('%d/%m/%Y')}   KHI - MAD",
        f"Arrival: {ret.strftime('%d/%m/%Y')}   MAD - KHI",
        "Baggage allowance: 30 KG",
    ])

    write_pdf(out / "hotel.pdf", [
        "BOOKING CONFIRMATION", "Booking.com",
        "Hotel Name: Hotel Madrid Centro", "City: Madrid",
        f"Guest Name: {full}",
        "Confirmation Number: BK-77219034",
        f"Check-in: {dep.strftime('%d/%m/%Y')}",
        f"Check-out: {ret.strftime('%d/%m/%Y')}",
        "10 nights, 1 room, breakfast included",
    ])

    write_pdf(out / "employment_letter.pdf", [
        "SYSTEMS LIMITED", "NO OBJECTION CERTIFICATE",
        f"Date: {(TODAY - timedelta(days=6)).strftime('%d/%m/%Y')}",
        "To Whom It May Concern",
        f"This is to certify that Mr. {full} is employed with Systems Limited.",
        "Designation: Senior Software Engineer",
        "Date of Joining: 03/02/2019",
        "Monthly Salary: PKR 385,000",
        f"Leave has been approved from {dep.strftime('%d/%m/%Y')} to "
        f"{ret.strftime('%d/%m/%Y')}.",
        "He will resume his duties immediately after returning to Pakistan.",
        "We have no objection to his travel. His position remains open.",
        "Contact: hr@systemsltd.com, +92 51 111 178 111",
        "Ali Hassan, Head of Human Resources",
    ])

    write_pdf(out / "cover_letter.pdf", [
        "COVER LETTER",
        f"Date: {(TODAY - timedelta(days=4)).strftime('%d/%m/%Y')}",
        "To the Visa Officer, Consulate General of Spain, Karachi",
        "Dear Sir/Madam,",
        f"I am writing to apply for a Schengen short-stay visa. My name is {full}",
        f"and I hold Pakistani passport {passport_no}.",
        f"Purpose of my visit: tourism. I intend to travel from "
        f"{dep.strftime('%d/%m/%Y')} to {ret.strftime('%d/%m/%Y')}.",
        "I will stay at Hotel Madrid Centro in Madrid for the full duration.",
        "I am funding this trip myself from my salary savings, as shown in the",
        "enclosed bank statement.",
        "I am employed as a Senior Software Engineer at Systems Limited in Islamabad",
        "and my approved leave ends on the date of my return. My wife and two children",
        "live in Islamabad and remain in Pakistan during my trip. I also own an",
        "apartment in Islamabad.",
        "I will return to Pakistan at the end of my visit to resume my employment.",
        "Yours faithfully,", full,
    ])

    write_pdf(out / "application_form.pdf", [
        "APPLICATION FOR SCHENGEN VISA", "FOR OFFICIAL USE ONLY",
        f"1. Surname: {name_sur}", f"2. First name(s): {name_giv}",
        f"3. Date of birth: {dob.strftime('%d/%m/%Y')}",
        f"Passport number: {passport_no}",
        f"Intended date of arrival: {dep.strftime('%d/%m/%Y')}",
        f"Intended date of departure: {ret.strftime('%d/%m/%Y')}",
    ])

    make_photo(out / "photo.jpg")
    return {"expect_score_at_least": 70, "name": full}


def bundle_problems(out: Path) -> dict:
    """A bundle seeded with the failures the rules are meant to catch."""
    dep = TODAY + timedelta(days=20)
    ret = dep + timedelta(days=14)
    name_sur, name_giv = "KHAN", "AHMED RAZA"
    passport_no = "AB1234567"
    dob = date(1990, 4, 12)
    # Passport expires only 20 days after return -> validity failure.
    expiry = ret + timedelta(days=20)

    l1, l2 = build_mrz(passport_no, name_sur, name_giv, dob, expiry)
    write_pdf(out / "passport.pdf", [
        "ISLAMIC REPUBLIC OF PAKISTAN", "PASSPORT",
        f"Passport No: {passport_no}",
        f"Date of Birth: {dob.strftime('%d/%m/%Y')}",
        f"Date of Expiry: {expiry.strftime('%d/%m/%Y')}",
        "Machine readable zone:", l1, l2,
    ], mono_from=6)

    # Statement: 2 months only, stale, low balance, one dominating deposit.
    rows = []
    balance = 60_000
    for i in range(8):
        d = TODAY - timedelta(days=95 - i * 7)
        amount = 9_000
        balance += amount
        rows.append(f"{d.strftime('%d/%m/%Y')}   Transfer   {amount:,.2f}   {balance:,.2f}")
    balance += 420_000
    rows.append(f"{(TODAY - timedelta(days=40)).strftime('%d/%m/%Y')}   "
                f"Cash deposit   420,000.00   {balance:,.2f}")

    write_pdf(out / "bank_statement.pdf", [
        "MEEZAN BANK", "STATEMENT OF ACCOUNT",
        # Name deliberately differs from the passport -> consistency failure.
        "Account Title: AHMAD R KHANN",
        "Currency: PKR",
        f"Statement Period: {(TODAY - timedelta(days=95)).strftime('%d/%m/%Y')} "
        f"to {(TODAY - timedelta(days=38)).strftime('%d/%m/%Y')}",
        "Opening Balance: 60,000.00",
        "Transaction Date  Details   Credit   Balance",
        *rows,
        f"Closing Balance: {balance:,.2f}",
    ])

    # Insurance: too little cover, expires before the trip ends, no repatriation.
    write_pdf(out / "insurance.pdf", [
        "TRAVEL INSURANCE CERTIFICATE",
        "Policy Number: TI-55021",
        "Insured Person: AHMED RAZA KHAN",
        "Sum Insured: EUR 15,000",
        "Coverage: Medical expenses only",
        f"Valid from {dep.strftime('%d/%m/%Y')} to "
        f"{(ret - timedelta(days=5)).strftime('%d/%m/%Y')}",
    ])

    write_pdf(out / "flight.pdf", [
        "E-TICKET", "Booking Reference: 9ZQW1M",
        "Passenger Name: AHMED RAZA KHAN",
        f"Departure: {dep.strftime('%d/%m/%Y')}   ISB - CDG",
        f"Arrival: {ret.strftime('%d/%m/%Y')}   CDG - ISB",
    ])

    make_photo(out / "photo.jpg", width=500, height=500,
               background=(40, 90, 160), blur=True)
    return {"expect_score_at_most": 45}


CASES = {"clean": bundle_clean, "problems": bundle_problems}


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate test document bundles.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--case", default="clean", choices=sorted(CASES))
    args = ap.parse_args()

    out = Path(args.out)
    meta = CASES[args.case](out)
    files = sorted(p.name for p in out.iterdir() if p.is_file())
    print(f"Wrote {len(files)} file(s) to {out}: {', '.join(files)}")
    if meta:
        print(f"Expectations: {meta}")


if __name__ == "__main__":
    main()
