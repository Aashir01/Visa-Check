# VisaGuard

Upload a visa document set, get a rejection-risk report before submitting.

VisaGuard checks an application bundle against a **versioned, per-corridor
checklist**: what is missing, what contradicts itself, whether the funds and
photo meet the stated thresholds, and how to fix each finding. It is a
document completeness checker, not an immigration adviser — it never claims an
application will be approved.

---

## What is built

| Blueprint phase | Status |
|---|---|
| 1 — Rule packs | Draft packs for the three launch corridors, marked unverified |
| 2 — Core pipeline | Upload → OCR → classify → extract → rules → score, driveable from the CLI |
| 3 — Report | Ranked issues with evidence and fix instructions, branded PDF |
| 4 — Client UI | Landing, new check, upload, report, history, account, auth |
| 5 — Admin | Overview, versioned rules editor, corridors, review queue, users, costs |
| 6 — Billing | **Not built.** Credits are tracked and enforced; no payment provider is wired |

---

## Quick start

Two processes: a FastAPI backend and a Next.js frontend.

### Backend

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Tesseract is the only system dependency (PDF rasterising uses pypdfium2).
sudo apt-get install -y tesseract-ocr

cp .env.example .env          # then edit SECRET_KEY at minimum
.venv/bin/python -m app.seed --admin-email you@yourdomain.com --admin-password 'a-strong-password'
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

API docs are then at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000` and sign in with the admin account you seeded.

### Without an API key

The app runs fine with no `ANTHROPIC_API_KEY`. Every deterministic check —
missing documents, name and date consistency, funds, validity windows, photo
compliance — still runs. Only the AI review of free-text letters is skipped,
and the report says so explicitly.

---

## The CLI

Phase 2 of the blueprint is "CLI only, no UI", because rule packs need testing
against real bundles before anyone sees a web page.

```bash
cd backend

.venv/bin/python cli.py corridors                      # list corridors and versions
.venv/bin/python cli.py validate app/rulepacks/uk_visitor_pk.json
.venv/bin/python cli.py check \
    --corridor schengen_short_stay_pk \
    --profile employed \
    --from 2026-09-10 --to 2026-09-20 \
    --pdf report.pdf --json result.json \
    ./anonymised-case-01/
.venv/bin/python cli.py purge                          # delete documents past retention
```

`check` exits `2` when any critical issue is found, so it can be scripted over
a folder of past cases — which is exactly what §8.4 of the blueprint asks for:
run 20 previously refused files through it and confirm the rules catch the
actual refusal reason.

Synthetic test bundles, for exercising the pipeline without real applicant data:

```bash
.venv/bin/python tests/make_fixtures.py --out /tmp/clean --case clean
.venv/bin/python tests/make_fixtures.py --out /tmp/bad   --case problems
```

---

## How a check runs

```
upload → OCR → classify → extract → rules → LLM review → score → report
```

Expensive steps run last, on the least data:

1. **OCR.** A born-digital PDF is read straight from its text layer — free, and
   more accurate than rasterise-then-OCR. Only scans and photos reach Tesseract.
2. **Classify.** Keyword signatures settle most documents instantly. Anything
   ambiguous goes to the model in **one batched call for the whole bundle**.
3. **Extract.** Per-type regex extractors, plus an ICAO 9303 MRZ parser whose
   check digits let us *verify* we read the passport correctly. One batched LLM
   call fills only the gaps regex could not, and never overwrites a
   deterministic value.
4. **Rules.** Deterministic evaluation of the corridor's rule pack.
5. **LLM review.** One call, only for what code cannot judge — whether an
   invitation letter states who is paying, whether an employment letter
   confirms approved leave.
6. **Score.** 100 minus severity-weighted, confidence-weighted penalties.

Two or three model calls per check, not one per document. That is the
difference between a check costing cents and costing dollars.

### Pass, fail, and "could not evaluate"

A rule returns one of three outcomes, and the third is not folded into the
first. If the bank statement is missing, the "statement is recent" rule reports
**not evaluated** — it does not report as passed. Reports list these
separately, because telling someone their file is fine when nothing looked at
it is the failure mode §9 warns about.

---

## Rule packs — the moat

A rule pack is data, not code. Editing a threshold in `/admin/rules` changes
product behaviour with no deploy.

```
backend/app/rulepacks/
  schengen_short_stay_pk.json
  uk_visitor_pk.json
  saudi_umrah_pk.json
```

Each pack carries the checklist (`documents`), the analytic rules (`rules`),
FX rates for cross-currency thresholds, severity weights, the disclaimer, and
the criteria for the AI letter review.

### Rule types

| Type | Checks |
|---|---|
| `field_consistency` | A field matches across documents (tolerant name matching) |
| `financial_sufficiency` | Balance vs per-day or fixed threshold, with FX conversion |
| `statement_recency` / `statement_history` | Statement freshness and period length |
| `sudden_deposit` | A single deposit dominating the balance |
| `passport_validity` | Validity beyond return, plus issue age |
| `date_coverage` | Insurance covering every day of travel |
| `date_order` | Cross-document chronology |
| `document_age` | Letters still in date at submission |
| `numeric_min` | Minimum insurance cover, etc. |
| `boolean_required` | A stated feature, e.g. repatriation cover |
| `photo_spec` | Size, DPI, head ratio, background, sharpness, colour |
| `profile_documents` | At least one of a set, e.g. proof of income |

Validation runs on save and on publish; a pack that references an unknown
document type, or that would never report anything missing, is rejected.

### Versioning

Published packs are **immutable**. Each check snapshots the version it ran
against, so editing a rule can never rewrite an existing report. To change a
published pack, save a new version — old reports keep theirs.

### ⚠️ The bundled packs are drafts

They were assembled from published requirements and are marked
`"unverified": true`, which makes every report carry a visible draft banner.
**They are not verified against live casework.** Before selling checks against
them:

- Correct each pack from your own files in `/admin/rules`.
- Verify the financial thresholds — Schengen figures are set per member state
  and revised annually; the UK sets no fixed threshold at all, and the number
  in that pack is an internal heuristic, not an official requirement.
- Re-check the FX rates, which are indicative placeholders.
- Run your 20 past refusals through the CLI. If fewer than 15 are caught, fix
  the rules before going further.
- Set `unverified: false` only once a pack reflects real casework.

---

## Cost control

§9 names LLM cost exceeding price as a live risk, so the budget is enforced
rather than reported. Once a check has spent `LLM_BUDGET_USD_PER_CHECK`,
further calls are refused and the check completes on deterministic findings
alone, saying so in the report.

`/admin/costs` breaks spend down by corridor and call type, and shows gross
margin at each price point in the blueprint, so an unprofitable corridor is
visible before it matters.

---

## Handling applicant documents

- Encrypted at rest with Fernet; the key derives from `SECRET_KEY`.
- Stored `0600`, never written to disk in plaintext. Decryption happens into a
  short-lived temp file only while a document is being read.
- Deleted automatically after `RETENTION_DAYS` (default 30). Reports survive
  the purge; source documents do not.
- Deleting a check removes its files immediately.

Run the purge daily:

```bash
0 3 * * *  cd /path/to/backend && .venv/bin/python cli.py purge
```

Rotating `SECRET_KEY` orphans stored documents, which given the 30-day window
is a deliberate trade — but do not rotate it casually.

---

## Configuration

Everything is env-overridable; see `backend/.env.example`.

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | dev placeholder | Auth tokens **and** document encryption. Startup refuses to boot with the default outside development |
| `DATABASE_URL` | SQLite | Point at Postgres in production |
| `ANTHROPIC_API_KEY` | empty | Omit to run deterministic-only |
| `LLM_BUDGET_USD_PER_CHECK` | `0.15` | Hard per-check ceiling |
| `OCR_PROVIDER` | `tesseract` | Or `claude_vision`; a pack can override per corridor via `ocr.provider` |
| `RETENTION_DAYS` | `30` | Document purge window |
| `LOW_CONFIDENCE_THRESHOLD` | `0.55` | Below this, a check is routed to the review queue |

### A note on OCR accuracy

Tesseract is the default because it is free, and the text-layer shortcut means
most real bundles never touch it. It is genuinely weak, however, on passport
MRZ bands and on skewed phone photos of documents — which is what applicants
actually upload. Two mitigations are built in:

- The MRZ parser validates ICAO check digits and repairs the OCR-B glyph
  confusions (`O`/`0`, `I`/`1`, `S`/`5`), recovering most misreads.
- A Claude vision OCR provider can be switched on per corridor when accuracy
  matters more than token cost.

If real-world classification accuracy disappoints, that switch is the first
thing to try.

---

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q     # 64 tests
cd frontend && npx tsc --noEmit && npm run build
```

The suite covers MRZ check digits and OCR repair, name matching, money and
date parsing, statement column disambiguation, FX conversion, every rule
outcome including "could not evaluate", scoring monotonicity and bounds, rule
pack validation, LLM budget enforcement, and the guard that stops a
hallucinated criterion becoming a finding.

---

## Project layout

```
backend/
  app/
    pipeline/       ocr, mrz, classify, extract, photo, rules_engine,
                    qualitative, scoring, runner, normalize
    rulepacks/      the three launch corridors as JSON
    report/pdf.py   branded PDF report
    api/            auth, corridors, checks, admin
    rulepack_schema.py   validation for the rules editor
  cli.py            phase-2 command-line runner
  tests/
frontend/
  app/              landing, auth, check flow, history, account, admin
  components/       shared UI
  lib/              api client, auth context, formatting
```

---

## Not built

- **Billing.** Credits are tracked and enforced, but no Paddle or Lemon
  Squeezy integration. §6 recommends a merchant of record for Pakistan.
- Cover letter generation, re-check after fixes, non-English output, API
  access — all v2 items, explicitly deferred until 20 paying users.
- Background job queue. Checks run in a FastAPI `BackgroundTask`, which is
  fine at this volume; move to a real worker before it is not.

---

## Disclaimer

VisaGuard reports whether a document set matches a named checklist at a stated
version and date. It does not give legal or eligibility advice, and nothing it
produces predicts the outcome of any visa application. Consular requirements
change without notice and vary between consulates and individual cases.
