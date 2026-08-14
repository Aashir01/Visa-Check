#!/usr/bin/env python3
"""Command-line runner — Phase 2 of the build order ("CLI only, no UI").

Run a bundle of documents through the full pipeline without touching the web
app. This is the tool for testing rule packs against real anonymised cases,
which §8 says to do before trusting any of it.

    python cli.py corridors
    python cli.py check --corridor schengen_short_stay_pk --profile employed \\
        --from 2026-09-10 --to 2026-09-20 --pdf out.pdf ./bundle/*.pdf
    python cli.py validate app/rulepacks/uk_visitor_pk.json
    python cli.py refusal ./past-refusals/ --corridor schengen_short_stay --verbose
    python cli.py purge
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path

from app.config import settings
from app.db import SessionLocal, init_db
from app.models import Check, CheckStatus, Corridor, Role, RulePack, User, utcnow
from app.pipeline.doctypes import label_for
from app.pipeline.runner import run_check
from app.report.pdf import build_report_pdf
from app.rulepack_schema import validate_pack
from app.security import hash_password
from app import storage

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
RED, YELLOW, BLUE, GREEN = "\033[31m", "\033[33m", "\033[34m", "\033[32m"
SEV_COLOR = {"critical": RED, "warning": YELLOW, "info": BLUE}


def _cli_user(db) -> User:
    user = db.query(User).filter(User.email == "cli@localhost").first()
    if not user:
        user = User(
            email="cli@localhost",
            password_hash=hash_password("cli-local-only"),
            full_name="CLI",
            role=Role.admin,
            credits=10_000,
        )
        db.add(user)
        db.commit()
    return user


def cmd_corridors(_args) -> int:
    db = SessionLocal()
    try:
        rows = db.query(Corridor).order_by(Corridor.label).all()
        if not rows:
            print("No corridors. Run: python -m app.seed")
            return 1
        for c in rows:
            pack = db.get(RulePack, c.active_rulepack_id) if c.active_rulepack_id else None
            flag = "enabled " if c.enabled else "disabled"
            version = pack.version if pack else "— no published pack —"
            warn = f" {YELLOW}[UNVERIFIED]{RESET}" if pack and pack.unverified else ""
            print(f"  {BOLD}{c.key}{RESET}  {flag}  v{version}{warn}")
            print(f"    {DIM}{c.label}{RESET}")
    finally:
        db.close()
    return 0


def cmd_validate(args) -> int:
    path = Path(args.path)
    if not path.exists():
        print(f"{RED}No such file: {path}{RESET}")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{RED}Invalid JSON: {exc}{RESET}")
        return 1

    errors = validate_pack(data)
    if errors:
        print(f"{RED}{len(errors)} problem(s) in {path.name}:{RESET}")
        for e in errors:
            print(f"  - {e}")
        return 1

    docs = data.get("documents", [])
    print(f"{GREEN}{path.name} is valid.{RESET}")
    print(f"  version   : {data.get('version')}")
    print(f"  documents : {len(docs)} ({sum(1 for d in docs if d.get('required'))} required)")
    print(f"  rules     : {len(data.get('rules', []))}")
    print(f"  llm checks: {len((data.get('llm_review') or {}).get('criteria', []))}")
    if data.get("unverified"):
        print(f"  {YELLOW}marked UNVERIFIED — reports will carry a draft banner{RESET}")
    return 0


def cmd_check(args) -> int:
    paths: list[Path] = []
    for pattern in args.files:
        p = Path(pattern)
        if p.is_dir():
            paths.extend(sorted(x for x in p.iterdir() if x.is_file()))
        elif p.exists():
            paths.append(p)
        else:
            print(f"{YELLOW}skipping missing file: {pattern}{RESET}")
    if not paths:
        print(f"{RED}No input files.{RESET}")
        return 1

    db = SessionLocal()
    try:
        corridor = db.query(Corridor).filter(Corridor.key == args.corridor).first()
        if not corridor:
            print(f"{RED}Unknown corridor '{args.corridor}'.{RESET} Try: python cli.py corridors")
            return 1
        if not corridor.active_rulepack_id:
            print(f"{RED}Corridor '{args.corridor}' has no published rule pack.{RESET}")
            return 1
        pack_row = db.get(RulePack, corridor.active_rulepack_id)

        user = _cli_user(db)
        check = Check(
            user_id=user.id,
            corridor_id=corridor.id,
            rulepack_id=pack_row.id,
            rulepack_version=pack_row.version,
            rulepack_unverified=pack_row.unverified,
            applicant_profile=args.profile,
            travel_from=getattr(args, "from"),
            travel_to=args.to,
            status=CheckStatus.draft,
        )
        db.add(check)
        db.flush()

        from app.models import Document

        for path in paths:
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            raw = path.read_bytes()
            doc = Document(
                check_id=check.id, filename=path.name, mime=mime, size_bytes=len(raw)
            )
            db.add(doc)
            db.flush()
            stored, digest = storage.save_document(check.id, doc.id, raw)
            doc.storage_path, doc.sha256 = stored, digest
        db.commit()

        print(f"{DIM}Running {len(paths)} document(s) against "
              f"{pack_row.data.get('title')} v{pack_row.version}...{RESET}")
        run_check(db, check, pack_row.data or {})
        db.refresh(check)

        if check.status != CheckStatus.complete:
            print(f"{RED}Check failed: {check.error}{RESET}")
            return 1

        _print_report(check, db)

        if args.pdf:
            pdf = build_report_pdf(
                check=check, corridor=corridor, pack=pack_row.data or {},
                documents=list(check.documents),
            )
            Path(args.pdf).write_bytes(pdf)
            print(f"\n{GREEN}PDF written to {args.pdf}{RESET}")

        if args.json:
            Path(args.json).write_text(
                json.dumps(
                    {
                        "check_id": check.id,
                        "risk_score": check.risk_score,
                        "risk_band": check.risk_band,
                        "summary": check.summary,
                        "confidence": check.confidence,
                        "issues": check.issues,
                        "extraction": check.extraction,
                        "llm_cost_usd": check.llm_cost_usd,
                    },
                    indent=2, default=str,
                ),
                encoding="utf-8",
            )
            print(f"{GREEN}JSON written to {args.json}{RESET}")

        return 0 if not any(
            i["severity"] == "critical" for i in (check.issues or [])
        ) else 2
    finally:
        db.close()


def _print_report(check: Check, db) -> None:
    extraction = check.extraction or {}
    scoring = extraction.get("scoring", {})
    band_colour = {"low": GREEN, "moderate": YELLOW, "elevated": YELLOW,
                   "high": RED}.get(check.risk_band, RESET)

    print()
    print("=" * 74)
    print(f"  {BOLD}RISK SCORE: {band_colour}{check.risk_score}/100"
          f"  ({scoring.get('band_label', '')}){RESET}")
    print("=" * 74)
    print(f"\n{check.summary}\n")

    print(f"{BOLD}Documents detected{RESET}")
    for d in check.documents:
        conf = d.doc_type_confidence or 0
        marker = GREEN if conf >= 0.75 else (YELLOW if conf >= 0.5 else RED)
        print(f"  {marker}●{RESET} {d.filename[:44]:<44} "
              f"{label_for(d.effective_type):<28} {DIM}{conf:.0%} · {d.ocr_engine}{RESET}")

    issues = check.issues or []
    if issues:
        print(f"\n{BOLD}Issues{RESET}")
        for i, issue in enumerate(issues, start=1):
            colour = SEV_COLOR.get(issue["severity"], RESET)
            print(f"\n  {colour}[{issue['severity'].upper()}]{RESET} "
                  f"{BOLD}{i}. {issue['title']}{RESET}")
            print(f"     {issue['detail']}")
            if issue.get("fix"):
                print(f"     {GREEN}Fix:{RESET} {issue['fix']}")
            if float(issue.get("confidence", 1)) < 0.6:
                print(f"     {DIM}(low confidence — verify manually){RESET}")

    passed = extraction.get("passed") or []
    if passed:
        print(f"\n{BOLD}Passed ({len(passed)}){RESET}")
        for p in passed:
            print(f"  {GREEN}✓{RESET} {p.get('title') or p.get('rule_id')}")

    skipped = extraction.get("skipped") or []
    if skipped:
        print(f"\n{BOLD}Not evaluated ({len(skipped)}){RESET} "
              f"{DIM}— missing or unreadable input; these did NOT pass{RESET}")
        for s in skipped:
            print(f"  {DIM}—{RESET} {s.get('title') or s.get('rule_id')}")

    print(f"\n{DIM}LLM cost: ${check.llm_cost_usd:.4f} · "
          f"{check.tokens_in} in / {check.tokens_out} out tokens · "
          f"{check.duration_ms}ms · confidence {check.confidence}{RESET}")
    if extraction.get("degraded_llm"):
        print(f"{YELLOW}Note: AI letter review did not run (no API key or budget "
              f"exhausted). Deterministic checks only.{RESET}")


def cmd_doctor(_args) -> int:
    """Verify the OCR engine actually works before trusting it in production.

    The configured engine falls back to Tesseract on any fault, which is the
    right runtime behaviour but hides a misconfiguration. This proves which
    engine is really running by putting a synthetic passport through it and
    checking the MRZ check digits validate.
    """
    import tempfile
    from datetime import date, timedelta

    from app.pipeline.ocr import PaddleOcrProvider, get_provider
    from app.pipeline.mrz import parse_mrz

    ok = True
    print(f"{BOLD}Configuration{RESET}")
    print(f"  OCR provider     : {settings.ocr_provider}")
    print(f"  worker mode      : {settings.worker_mode}")
    print(f"  free tier AI     : {'on' if settings.free_tier_ai_enabled else 'off (deterministic only)'}")
    print(f"  LLM key          : {'set' if settings.anthropic_api_key else 'not set'}")
    print(f"  retention        : {settings.retention_days} days")

    print(f"\n{BOLD}Engines{RESET}")
    try:
        import pytesseract

        print(f"  {GREEN}OK{RESET}   tesseract {pytesseract.get_tesseract_version()}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  {RED}FAIL{RESET} tesseract unavailable: {exc}")

    if settings.ocr_provider in ("paddleocr", "paddle"):
        if PaddleOcrProvider.available():
            print(f"  {GREEN}OK{RESET}   paddleocr importable")
        else:
            ok = False
            print(f"  {RED}FAIL{RESET} paddleocr NOT importable — checks will silently "
                  f"fall back to Tesseract.")
            print(f"         fix: pip install paddlepaddle paddleocr")

    # --- end-to-end: photograph a passport and try to read it back ---
    print(f"\n{BOLD}Live OCR test{RESET} {DIM}(synthetic passport, simulated phone photo){RESET}")
    try:
        from tests.make_fixtures import build_mrz, write_pdf
        from tests.make_phone_photo import degrade, render_pdf_page

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            dob, expiry = date(1990, 4, 12), date.today() + timedelta(days=1500)
            l1, l2 = build_mrz("AB1234567", "KHAN", "AHMED RAZA", dob, expiry)
            write_pdf(tmp / "p.pdf", [
                "ISLAMIC REPUBLIC OF PAKISTAN", "PASSPORT",
                "Passport No: AB1234567",
                f"Date of Birth: {dob.strftime('%d/%m/%Y')}",
                f"Date of Expiry: {expiry.strftime('%d/%m/%Y')}",
                "Machine readable zone:", l1, l2,
            ], mono_from=6)

            photo = tmp / "p.jpg"
            degrade(render_pdf_page(tmp / "p.pdf"), level="light", seed=7).save(photo, quality=85)

            provider = get_provider(settings.ocr_provider)
            result = provider.extract(photo, "image/jpeg")
            mrz = parse_mrz(result.text)

            print(f"  engine actually used : {result.engine}")
            if result.engine != settings.ocr_provider and settings.ocr_provider != "tesseract":
                ok = False
                print(f"  {RED}FAIL{RESET} fell back to '{result.engine}' instead of "
                      f"'{settings.ocr_provider}'")
            print(f"  characters recovered : {len(result.text.strip())}")
            print(f"  lines recovered      : {len(result.text.splitlines())}")

            if mrz.document_number == "AB1234567" and mrz.valid:
                print(f"  {GREEN}OK{RESET}   MRZ read and all check digits validated")
            elif mrz.document_number:
                ok = False
                print(f"  {YELLOW}WARN{RESET} MRZ found ({mrz.document_number}) but check "
                      f"digits did not all validate: {mrz.checks}")
            else:
                ok = False
                print(f"  {RED}FAIL{RESET} MRZ not recovered from a lightly degraded photo. "
                      f"Passport extraction will be unreliable.")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  {RED}FAIL{RESET} live OCR test errored: {exc}")

    print()
    if ok:
        print(f"{GREEN}All checks passed.{RESET}")
        return 0
    print(f"{RED}Some checks failed — see above before serving real traffic.{RESET}")
    return 1


def cmd_refusal(args) -> int:
    """Decode refusal letters from the terminal, one or a folder at a time.

    The README tells an operator to run past refusals through the tool before
    trusting the rule packs, which until now meant doing it one upload at a
    time through the web app. A folder of anonymised letters is the realistic
    shape of that work, and the summary at the end is the number that matters:
    how often the deterministic path was enough, and which grounds keep coming
    up in your own casework.
    """
    from app.refusal import build, decode_text, from_manual, ground

    paths: list[Path] = []
    if args.codes:
        pass
    else:
        for pattern in args.files or []:
            p = Path(pattern)
            if p.is_dir():
                paths.extend(sorted(x for x in p.iterdir() if x.is_file()))
            elif p.exists():
                paths.append(p)
            else:
                print(f"{YELLOW}skipping missing file: {pattern}{RESET}")
        if not paths:
            print(f"{RED}Give one or more refusal letters, or --codes 3,7.{RESET}")
            return 1

    db = SessionLocal()
    try:
        pack = None
        if args.corridor:
            corridor = db.query(Corridor).filter(Corridor.key == args.corridor).first()
            if not corridor:
                print(f"{RED}Unknown corridor '{args.corridor}'.{RESET}")
                return 1
            if corridor.active_rulepack_id:
                row = db.get(RulePack, corridor.active_rulepack_id)
                pack = row.data if row else None

        if args.codes:
            cases = [("--codes", from_manual([c.strip() for c in args.codes.split(",")]))]
        else:
            cases = []
            for path in paths:
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                if mime.startswith("text/") or path.suffix.lower() in {".txt", ".md"}:
                    text = path.read_text(errors="replace")
                else:
                    from app.pipeline.ocr import get_provider

                    text = get_provider().extract(path, mime).text or ""
                cases.append((path.name, decode_text(text)))

        tally: dict[str, int] = {}
        deterministic = 0
        for name, decoded in cases:
            plan = build(decoded, pack)
            print(f"\n{BOLD}{name}{RESET}")
            if not decoded.grounds:
                print(f"  {YELLOW}no grounds identified{RESET} — "
                      "is this the page with the numbered boxes?")
                continue
            deterministic += decoded.method in ("deterministic", "manual")
            print(f"  method     : {decoded.method} ({decoded.confidence:.0%} confidence)")
            if decoded.consulate:
                print(f"  consulate  : {decoded.consulate}")
            if decoded.decision_date:
                print(f"  decided    : {decoded.decision_date}")
            colour = GREEN if plan["verdict"] == "reapply" else YELLOW
            if plan["verdict"] == "seek_advice":
                colour = RED
            print(f"  verdict    : {colour}{plan['verdict']}{RESET} — {plan['headline']}")
            for g in decoded.grounds:
                tally[g.code] = tally.get(g.code, 0) + 1
                mark = "" if g.fixable else f" {RED}(not fixable by reapplying){RESET}"
                print(f"    {g.number:>2}. {g.plain}{mark}")
                if args.verbose:
                    rules = ", ".join(g.rule_ids) or f"{RED}no rules cover this ground{RESET}"
                    print(f"        rules: {DIM}{rules}{RESET}")

        decoded_count = sum(1 for _, d in cases if d.grounds)
        print(f"\n{BOLD}{len(cases)} letter(s): {decoded_count} decoded, "
              f"{len(cases) - decoded_count} not{RESET}")
        if decoded_count:
            print(f"  without a model call: {deterministic}/{decoded_count}")
        if tally:
            print("  grounds seen:")
            for code, n in sorted(tally.items(), key=lambda kv: -kv[1]):
                g = ground(code)
                flag = "" if g.rule_ids else f"  {RED}<- no rule covers this{RESET}"
                print(f"    {n:>3}x  {g.number:>2}. {code}{flag}")
        return 0
    finally:
        db.close()


def cmd_purge(_args) -> int:
    db = SessionLocal()
    try:
        result = storage.purge_expired(db)
        print(f"Purged documents for {result['checks_purged']} check(s) and "
              f"{result['refusals_purged']} refusal(s), "
              f"{result['files_removed']} file(s) removed "
              f"(retention: {settings.retention_days} days).")
    finally:
        db.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cli.py", description="VisaGuard command-line runner."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("corridors", help="List corridors and their rule pack versions.")

    v = sub.add_parser("validate", help="Validate a rule pack JSON file.")
    v.add_argument("path")

    c = sub.add_parser("check", help="Run a document bundle through the pipeline.")
    c.add_argument("files", nargs="+", help="Files or a directory of files.")
    c.add_argument("--corridor", required=True)
    c.add_argument("--profile", default="employed",
                   choices=["employed", "self_employed", "student", "retired"])
    c.add_argument("--from", dest="from", help="Travel start date, YYYY-MM-DD.")
    c.add_argument("--to", help="Travel end date, YYYY-MM-DD.")
    c.add_argument("--pdf", help="Write the PDF report here.")
    c.add_argument("--json", help="Write the raw result JSON here.")

    r = sub.add_parser("refusal", help="Decode refusal letters and summarise the grounds.")
    r.add_argument("files", nargs="*", help="Letters, or a directory of them.")
    r.add_argument("--codes", help="Skip decoding and name the grounds, e.g. 3,7.")
    r.add_argument("--corridor", help="Tie each ground to this corridor's checklist.")
    r.add_argument("--verbose", action="store_true",
                   help="Show which rules cover each ground.")

    sub.add_parser("purge", help="Delete stored documents past the retention window.")
    sub.add_parser("doctor", help="Verify OCR, config and the pipeline end to end.")

    args = parser.parse_args()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    init_db()

    return {
        "corridors": cmd_corridors,
        "validate": cmd_validate,
        "check": cmd_check,
        "refusal": cmd_refusal,
        "purge": cmd_purge,
        "doctor": cmd_doctor,
    }[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
