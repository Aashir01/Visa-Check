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
    {
        "key": "schengen_short_stay_pk",
        "origin_country": "PK",
        "destination": "Schengen Area",
        "visa_type": "short_stay_c",
        "label": "Schengen short-stay (Type C) — from Pakistan",
        "description": (
            "Tourism, family visit or business travel of up to 90 days in any "
            "180-day period."
        ),
        "pack": "schengen_short_stay_pk.json",
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
