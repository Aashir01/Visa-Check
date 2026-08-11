"""Seed corridors, rule packs and an admin account."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, init_db
from .models import Corridor, Role, RulePack, RulePackStatus, User, utcnow
from .rulepack_schema import validate_pack
from .security import hash_password

log = logging.getLogger(__name__)
PACK_DIR = Path(__file__).parent / "rulepacks"

CORRIDORS = [
    # ── Schengen ──
    {
        "key": "schengen_short_stay",
        "origin_country": "GLOBAL",
        "destination": "Schengen Area",
        "visa_type": "short_stay_c",
        "label": "Schengen short-stay (Type C) — Global",
        "description": "Tourism, family visit or business travel of up to 90 days in any 180-day period. Covers all 29 Schengen countries. Visa-required or visa-free depending on your nationality.",
        "pack": "schengen_short_stay.json",
    },
    {
        "key": "schengen_short_stay_pk",
        "origin_country": "PK",
        "destination": "Schengen Area",
        "visa_type": "short_stay_c",
        "label": "Schengen short-stay (Type C) — from Pakistan",
        "description": "Tourism, family visit or business travel of up to 90 days in any 180-day period.",
        "pack": "schengen_short_stay_pk.json",
    },
    # ── United Kingdom ──
    {
        "key": "uk_standard_visitor",
        "origin_country": "GLOBAL",
        "destination": "United Kingdom",
        "visa_type": "standard_visitor",
        "label": "UK Standard Visitor — Global",
        "description": "Tourism, family visit, business meetings, or short study (up to 6 months). Visa-required, ETA, or visa-free depending on nationality.",
        "pack": "uk_standard_visitor.json",
    },
    {
        "key": "uk_visitor_pk",
        "origin_country": "PK",
        "destination": "United Kingdom",
        "visa_type": "standard_visitor",
        "label": "UK Standard Visitor — from Pakistan",
        "description": "Tourism, family visit or business visit of up to 6 months.",
        "pack": "uk_visitor_pk.json",
    },
    # ── United States ──
    {
        "key": "usa_b1b2",
        "origin_country": "GLOBAL",
        "destination": "United States of America",
        "visa_type": "b1_b2",
        "label": "USA B1/B2 Visitor Visa — Global",
        "description": "Tourism, visiting family/friends, business meetings, or medical treatment. B1/B2 visa or ESTA (Visa Waiver Program) depending on nationality.",
        "pack": "usa_b1b2.json",
    },
    # ── Canada ──
    {
        "key": "canada_visitor",
        "origin_country": "GLOBAL",
        "destination": "Canada",
        "visa_type": "temporary_resident",
        "label": "Canada Visitor Visa (TRV) — Global",
        "description": "Tourism, visiting family/friends, or business visits. TRV, eTA, or visa-exempt depending on nationality.",
        "pack": "canada_visitor.json",
    },
    # ── Australia ──
    {
        "key": "australia_visitor",
        "origin_country": "GLOBAL",
        "destination": "Australia",
        "visa_type": "visitor_600",
        "label": "Australia Visitor Visa — Global",
        "description": "Tourism, visiting family/friends, or business visitor activities. Subclass 600, ETA (601), or eVisitor (651) depending on nationality.",
        "pack": "australia_visitor.json",
    },
    # ── UAE ──
    {
        "key": "uae_tourist",
        "origin_country": "GLOBAL",
        "destination": "United Arab Emirates",
        "visa_type": "tourist",
        "label": "UAE Tourist / Visit Visa — Global",
        "description": "Tourism and visiting in Dubai, Abu Dhabi, and other emirates. Visa-on-arrival, visa-free, or pre-arranged visa depending on nationality.",
        "pack": "uae_tourist.json",
    },
    # ── Japan ──
    {
        "key": "japan_tourist",
        "origin_country": "GLOBAL",
        "destination": "Japan",
        "visa_type": "temporary_visitor",
        "label": "Japan Temporary Visitor Visa — Global",
        "description": "Tourism, visiting friends/family, or short business trips (up to 90 days). Visa-free for 71 nationalities; visa required for others.",
        "pack": "japan_tourist.json",
    },
    # ── Turkey ──
    {
        "key": "turkey_tourist",
        "origin_country": "GLOBAL",
        "destination": "Turkey",
        "visa_type": "tourist",
        "label": "Turkey Tourist / e-Visa — Global",
        "description": "Tourism and visiting in Turkey. e-Visa (online, most nationalities), visa-free, or sticker visa from embassy depending on nationality.",
        "pack": "turkey_tourist.json",
    },
    # ── Saudi Arabia ──
    {
        "key": "saudi_umrah_pk",
        "origin_country": "PK",
        "destination": "Saudi Arabia",
        "visa_type": "umrah",
        "label": "Saudi Arabia Umrah — from Pakistan",
        "description": "Umrah pilgrimage visa, normally issued through a licensed agent.",
        "pack": "saudi_umrah_pk.json",
    },
]


def seed(db: Session, *, admin_email: str | None = None,
         admin_password: str | None = None, reset_packs: bool = False) -> dict:
    created = {"corridors": 0, "rulepacks": 0, "admin": None, "warnings": []}

    for spec in CORRIDORS:
        corridor = db.query(Corridor).filter(Corridor.key == spec["key"]).first()
        if not corridor:
            corridor = Corridor(
                key=spec["key"],
                origin_country=spec["origin_country"],
                destination=spec["destination"],
                visa_type=spec["visa_type"],
                label=spec["label"],
                description=spec["description"],
                enabled=True,
            )
            db.add(corridor)
            db.flush()
            created["corridors"] += 1

        pack_path = PACK_DIR / spec["pack"]
        if not pack_path.exists():
            created["warnings"].append(f"missing rule pack file: {pack_path.name}")
            continue

        data = json.loads(pack_path.read_text(encoding="utf-8"))
        errors = validate_pack(data)
        if errors:
            created["warnings"].append(
                f"{spec['key']} rule pack is invalid: {'; '.join(errors[:5])}"
            )
            continue

        version = data.get("version", "0.1.0-draft")
        existing = (
            db.query(RulePack)
            .filter(RulePack.corridor_id == corridor.id, RulePack.version == version)
            .first()
        )

        if existing and reset_packs:
            existing.data = data
            existing.unverified = bool(data.get("unverified", True))
            pack = existing
        elif existing:
            pack = existing
        else:
            pack = RulePack(
                corridor_id=corridor.id,
                version=version,
                data=data,
                unverified=bool(data.get("unverified", True)),
                notes="Seeded from bundled draft rule pack. Verify before relying on it.",
                status=RulePackStatus.draft,
            )
            db.add(pack)
            db.flush()
            created["rulepacks"] += 1

        if not corridor.active_rulepack_id or reset_packs:
            pack.status = RulePackStatus.published
            pack.published_at = pack.published_at or utcnow()
            corridor.active_rulepack_id = pack.id

    if admin_email and admin_password:
        email = admin_email.lower().strip()
        # The login endpoint validates with EmailStr, which rejects reserved
        # TLDs such as .local. Without the same check here, seeding happily
        # creates an admin account that can never sign in.
        try:
            from email_validator import validate_email

            validate_email(email, check_deliverability=False)
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(
                f"Refusing to seed admin '{email}': {exc}\n"
                "Use a normal address such as admin@yourdomain.com — reserved "
                "domains like .local are rejected at login."
            ) from exc

        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = Role.admin
            user.password_hash = hash_password(admin_password)
            created["admin"] = f"{email} (updated)"
        else:
            db.add(User(
                email=email,
                password_hash=hash_password(admin_password),
                full_name="Administrator",
                role=Role.admin,
                credits=1000,
            ))
            created["admin"] = f"{email} (created)"

    db.commit()
    return created


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Seed the VisaGuard database.")
    parser.add_argument("--admin-email")
    parser.add_argument("--admin-password")
    parser.add_argument(
        "--reset-packs", action="store_true",
        help="Overwrite bundled rule packs with the files on disk and republish them.",
    )
    args = parser.parse_args()

    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        result = seed(
            db,
            admin_email=args.admin_email,
            admin_password=args.admin_password,
            reset_packs=args.reset_packs,
        )
    finally:
        db.close()

    print("Seed complete:")
    print(f"  corridors created : {result['corridors']}")
    print(f"  rule packs created: {result['rulepacks']}")
    if result["admin"]:
        print(f"  admin             : {result['admin']}")
    for w in result["warnings"]:
        print(f"  WARNING           : {w}")


if __name__ == "__main__":
    main()
