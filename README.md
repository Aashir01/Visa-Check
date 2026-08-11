# VisaGuard

Upload a visa document set, get a rejection-risk report before submitting.

VisaGuard checks an application bundle against a **versioned, per-corridor
checklist**: what is missing, what contradicts itself, whether the funds and
photo meet the stated thresholds, and how to fix each finding. It is a
document completeness checker, not an immigration adviser — it never claims an
application will be approved.

---

## What is built

| Feature | Status |
|---|---|
| 1 — Rule packs | **11 corridors across 9 destinations** (Global + Pakistan-origin), sourced to official regulations |
| 2 — Core pipeline | Upload → OCR → classify → extract → rules → score, driveable from the CLI |
| 3 — Report | Ranked issues with evidence and fix instructions, branded PDF |
| 4 — Client UI | **Dark neon theme** with Orbitron + Share Tech Mono fonts, risk gauge, drag & drop |
| 5 — Admin | Overview, versioned rules editor, corridors, review queue, users, costs |
| 6 — LLM | **Multi-provider:** Anthropic (Claude) + **DeepSeek** — pluggable backends with auto-fallback |
| 7 — Billing | **Not built.** Credits and tiers are tracked; no payment provider is wired |

Plus, for a free public launch: a free tier that costs $0 per check, a job
queue, and rate limiting.

---

## Quick start

Two processes: a FastAPI backend and a Next.js frontend.

### Backend

```bash
cd backend

# Windows
py -3.13 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Tesseract is the only system dependency (PDF rasterising uses pypdfium2,
# and PP-OCR ships as a Python wheel).
# Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
# or: winget install UB-Mannheim.TesseractOCR
# macOS: brew install tesseract
# Linux: sudo apt-get install -y tesseract-ocr

cp .env.example .env          # then edit SECRET_KEY at minimum
.venv/bin/python -m app.seed --admin-email you@yourdomain.com --admin-password 'a-strong-password'
.venv/bin/python cli.py doctor        # confirm OCR actually works
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

API docs are then at `http://localhost:8000/docs`.

PP-OCR downloads its models on first use, so the machine needs outbound access
to HuggingFace or ModelScope once. If it cannot reach them, checks fall back to
Tesseract — `cli.py doctor` and `/health` both tell you when that is happening.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000` and sign in with the admin account you seeded.

### Without an API key

The app runs fine with **no API key at all**. Every deterministic check —
missing documents, name and date consistency, funds, validity windows, photo
compliance — still runs. Only the AI review of free-text letters is skipped,
and the report says so explicitly.

### With an LLM (Claude or DeepSeek)

Set `LLM_PROVIDER` to `anthropic` or `deepseek` and provide the corresponding
API key:

```env
# Option A: Anthropic (Claude)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Option B: DeepSeek (much cheaper — ~$0.14/M in / $0.28/M out)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
LLM_MODEL=deepseek-chat
LLM_PRICE_IN_PER_MTOK=0.14
LLM_PRICE_OUT_PER_MTOK=0.28
```

Both providers can be configured at once. If your preferred provider has no
key, the system auto-falls back to the other. The pipeline enforces a hard
per-check budget (`LLM_BUDGET_USD_PER_CHECK`, default $0.15) and degrades to
deterministic-only rather than silently burning margin.

---

## Tiers: why free traffic is survivable

A free check runs **deterministic rules only** and therefore costs nothing but
CPU. That is not a crippled product — it is most of the product:

| | Free | Full |
|---|---|---|
| Missing documents, per profile | ✓ | ✓ |
| Name / DOB / passport-number consistency | ✓ | ✓ |
| Funds vs corridor threshold, with FX | ✓ | ✓ |
| Statement recency, history, sudden deposits | ✓ | ✓ |
| Passport & insurance validity windows | ✓ | ✓ |
| Photo compliance | ✓ | ✓ |
| AI review of invitation / employment / cover letters | — | ✓ |

On the test bundle a free check produces **21 verified requirements and a
score of 91 at $0.00**. Only the letter review costs tokens.

Measured spend for a full check (~1,871 in / 1,500 out tokens):

| Model | Per check | 1,000/day | 10,000/day |
|---|---|---|---|
| Sonnet 5 | $0.028 | $843/mo | $8,434/mo |
| Haiku 4.5 | $0.009 | $281/mo | $2,811/mo |

That is the whole argument for the split. New accounts get
`FREE_AI_CREDITS_PER_USER` full checks so the upsell is a demonstration rather
than a claim. Set `FREE_TIER_AI_ENABLED=true` to give everyone AI — then watch
`/admin/costs`, because the bill now scales with traffic.

Reports always say which tier produced them, and distinguish "not included on
your plan" from "we tried and it failed".

## Running under load

Checks are CPU-bound (OCR), so in production the API should not run them:

```bash
WORKER_MODE=queue python -m uvicorn app.main:app --port 8000   # API
WORKER_MODE=queue python worker.py --concurrency 4             # worker(s)
```

`WORKER_MODE=inline` (the default) runs checks in a FastAPI background task,
which is fine for development and low volume. The queue is a claim-by-update
against the `checks` table — no Redis or Celery to deploy. Several workers can
run at once; a job abandoned by a crashed worker returns to the queue after
`WORKER_STALE_MINUTES`, and one that fails repeatedly is stopped rather than
looping forever.

Queue depth and the oldest pending job appear on `/admin` and `/health`.

### Abuse controls

A free upload endpoint on the public internet needs limits. All are
configurable, and enforced **per process** — exact on one instance, per-instance
behind several:

| Limit | Default |
|---|---|
| Checks per account per day | 20 |
| Checks per IP per hour | 10 |
| Uploads per IP per hour | 120 |
| Auth attempts per IP per hour | 20 |
| Total bytes per bundle | 60 MB |

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
.venv/bin/python cli.py doctor                         # verify OCR + config end to end
```

`doctor` is the one to run before serving real traffic. Because the OCR layer
falls back to Tesseract on any fault — right at runtime, misleading in
practice — `doctor` proves which engine is *actually* running by putting a
simulated phone photo of a passport through it and checking the MRZ check
digits validate:

```
Engines
  OK   tesseract 5.3.4
  OK   paddleocr importable
Live OCR test (synthetic passport, simulated phone photo)
  engine actually used : tesseract
  FAIL fell back to 'tesseract' instead of 'paddleocr'
```

`/health` reports the same thing as `ocr_provider_ready` and
`ocr_engine_in_use`.

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
  schengen_short_stay.json       # 29 Schengen countries, per-state funds
  uk_standard_visitor.json       # UK Standard Visitor (global)
  usa_b1b2.json                  # US B1/B2 (global)
  canada_visitor.json            # Canada TRV (global)
  australia_visitor.json         # Australia subclass 600 (global)
  uae_tourist.json               # UAE tourist/e-visa (global)
  japan_tourist.json             # Japan temporary visitor (global)
  turkey_tourist.json            # Turkey tourist/e-visa (global)
  schengen_short_stay_pk.json    # Schengen — from Pakistan
  uk_visitor_pk.json             # UK — from Pakistan
  saudi_umrah_pk.json            # Saudi Umrah — from Pakistan
```

**11 corridors, 9 destinations, any origin country.** Each global pack works
for any passport holder — it tells you which documents are needed regardless
of whether your nationality requires a visa, ETA, e-Visa, or is visa-free.

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

### Provenance: law vs our opinion

Every rule and document declares an `authority`, and reports show it:

| Authority | Meaning |
|---|---|
| `law` | Statute or regulation, e.g. EU Visa Code Art. 15. Cites its source. |
| `member_state` | A state's own published figure, e.g. Spain's SMI-linked amount. Cites its source. |
| `official_guidance` | Published consulate or ministry guidance. |
| `heuristic` | **Our own calibration. Not an official requirement.** |

The validator refuses to save a pack where a rule claims `law` or
`member_state` without citing a source, so nothing can be presented as
official without saying where it is written. On the test bundle a Schengen
report cites the Visa Code on 11 findings and flags 5 as our own guidance.

### Schengen funds are per member state

Published reference amounts range from **EUR 34/day (Netherlands) to
EUR 122.10/day (Spain)** — a factor of three. The pack therefore resolves the
figure from the destination:

```json
"per_destination": {
  "ES": { "per_day_amount": 122.10, "minimum_total": 1098.90 },
  "NL": { "per_day_amount": 34.00 },
  "DE": { "per_day_amount": 45.00 }
}
```

Set `applicant_meta.destination_country` (ISO-3166 alpha-2) on the check.
Without it the pack falls back to Spain.

Spain's figure is not a fixed number: Orden PRE/1282/2007 sets it at 10% of
gross SMI per day with a floor of 90% of SMI. SMI 2026 is EUR 1,221/month,
giving EUR 122.10/day and a EUR 1,098.90 floor. **When SMI changes each
January, update those two numbers and Spain is current again.**

### What the research changed

| | Before | After | Why |
|---|---|---|---|
| Schengen funds | EUR 100/day flat, EUR 800 floor | Per state; ES EUR 122.10/day, EUR 1,098.90 floor | Amounts are set per member state, not EU-wide |
| UK funds floor | GBP 1,500 | GBP 800 | The old figure was ~2x what practitioners describe; UK sets no official minimum at all |
| UK TB certificate | absent | Optional, >6-month stays only | Not required for a standard 6-month visit |
| Saudi mahram | "relaxed", vague | Optional, all ages, licensed group | Policy now permits women of any age without a mahram |
| Passport rules | asserted | Cited to Visa Code Art. 12 | 3 months beyond departure, 2 blank pages, issued within 10 years |
| EES / ETIAS | absent | Documented in pack notes | EES live since 10 Apr 2026; ETIAS is for visa-*exempt* nationals, so it does **not** apply to Pakistani applicants |

### ⚠️ The bundled packs are still drafts

They are now researched and sourced against official material — the EU Visa
Code, UKVI Appendix V, GOV.UK, and Saudi Ministry of Hajj / Nusuk guidance —
but they are still marked `"unverified": true` and every report carries a
draft banner. Sourced is not the same as verified: requirements change without
notice, vary between consulates, and the only thing that closes that gap is
your own casework. Before selling checks against them:

- Correct each pack from your own files in `/admin/rules`.
- Re-check the per-state Schengen amounts and Spain's SMI each January.
- Replace the UK funds heuristic with a figure from your own refusal data.
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
| `SECRET_KEY` | dev placeholder | Auth tokens **and** document encryption |
| `DATABASE_URL` | SQLite | Point at Postgres in production |
| `LLM_PROVIDER` | `anthropic` | `anthropic` or `deepseek` — choose your AI provider |
| `ANTHROPIC_API_KEY` | empty | Claude API key |
| `DEEPSEEK_API_KEY` | empty | DeepSeek API key (~20x cheaper per token) |
| `LLM_BUDGET_USD_PER_CHECK` | `0.15` | Hard per-check ceiling |
| `OCR_PROVIDER` | `paddleocr` | `tesseract`, `paddleocr`, or `claude_vision` |
| `RETENTION_DAYS` | `30` | Document purge window |

### Choosing an OCR engine

Three providers sit behind one interface, so switching is a config change:

| Provider | Cost per page | Runs on | Good for |
|---|---|---|---|
| `tesseract` | free | CPU | Digital PDFs and clean scans |
| `paddleocr` | free | CPU (GPU optional) | Phone photos, skew, uneven lighting |
| `claude_vision` | tokens | API | Worst-case images, when accuracy beats cost |

Set `OCR_PROVIDER`, or override per corridor with `ocr.provider` in a rule
pack so you only pay for accuracy where it earns its keep.

`paddleocr` needs an extra install and a one-time model download:

```bash
pip install paddlepaddle paddleocr
```

### Measured: where Tesseract stops working

Tesseract was benchmarked against simulated phone photos — perspective, skew,
a shadow gradient, and JPEG recompression — scoring whether the passport MRZ
could be recovered *and* its ICAO check digits validated:

| Degradation | Text recovered | MRZ found | Check digits |
|---|---|---|---|
| Light (slight skew, mild compression) | 330 chars | yes | 3/3 valid |
| Medium (~120 DPI effective, blur, JPEG 55) | 122 chars | no | — |
| Harsh (heavy blur, JPEG 35) | 89 chars | no | — |

The cliff between light and medium is steep and **preprocessing does not fix
it**: CLAHE, denoising, sharpening and adaptive thresholding were each
measured and all made recognition *worse*, amplifying JPEG noise faster than
they recovered strokes. Plain upscaling to ~1800px was the only transform that
helped, and it is the only one applied.

So: Tesseract is fine for digital PDFs, which is most of a typical bundle
(bank statements, e-tickets, insurance certificates are nearly always
born-digital and bypass OCR entirely via the text layer). Passports and CNICs
are the documents applicants photograph, and those are exactly where it fails.
If your traffic is phone-photo heavy, move to `paddleocr`.

`PaddleOcrProvider` could not be benchmarked in the build environment — the
model hosts (HuggingFace, ModelScope, BOS) are unreachable from it, so the
provider is written and unit-tested but its accuracy on your traffic is
unverified. Benchmark it yourself before switching:

```bash
python tests/make_phone_photo.py --pdf passport.pdf --out photo.jpg --level medium
OCR_PROVIDER=paddleocr python cli.py check --corridor schengen_short_stay_pk photo.jpg
```

### Why the MRZ matters so much

The MRZ is the only place in a bundle where a field can be *verified* rather
than merely read: ICAO 9303 check digits mean a recovered passport number is
either right or detectably wrong. The parser also repairs the OCR-B glyph
confusions (`O`/`0`, `I`/`1`, `S`/`5`) and re-checks.

This is worth guarding. An early bug flattened Tesseract's word output into a
single line, which made the two-line MRZ impossible to locate and silently
disabled verified passport extraction for *every image upload* — while digital
PDFs, which keep their newlines, kept working and hid the problem in tests.
`tests/test_ocr_lines.py` now pins the line structure end to end.

---

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q     # 126 tests
cd frontend && npx tsc --noEmit && npm run build
```

The suite covers MRZ check digits and OCR repair, name matching, money and
date parsing, statement column disambiguation, FX conversion, every rule
outcome including "could not evaluate", scoring monotonicity and bounds, rule
pack validation, LLM budget enforcement, and the guard that stops a
hallucinated criterion becoming a finding, the free/paid entitlement split,
queue claim semantics and stale-job recovery, rate limiting, rule-pack
provenance, and per-destination funds thresholds.

---

## Project layout

```
backend/
  app/
    pipeline/       ocr, mrz, classify, extract, photo, rules_engine,
                    qualitative, scoring, runner, normalize, llm (multi-provider)
    rulepacks/      11 corridor packs — 8 global + 3 Pakistan-origin
    report/pdf.py   branded PDF report
    api/            auth, corridors, checks, admin
    rulepack_schema.py   validation for the rules editor
  cli.py            command-line runner
  tests/
frontend/
  app/              landing (dark neon theme), auth, check flow, history, account, admin
  components/       shared UI (nav, ui primitives with glow effects)
  lib/              api client, auth context, formatting
  tailwind.config.ts  neon green palette, Orbitron + Share Tech Mono fonts
```

---

## Not built

- **Billing.** Credits are tracked and enforced, but no Paddle or Lemon
  Squeezy integration. §6 recommends a merchant of record for Pakistan.
- Cover letter generation, re-check after fixes, non-English output, API
  access — all v2 items, explicitly deferred until 20 paying users.
- Anonymous checks. Running a check requires an account, which is a
  conversion cost on a traffic-first launch but keeps every user attributable.

---

## Disclaimer

VisaGuard reports whether a document set matches a named checklist at a stated
version and date. It does not give legal or eligibility advice, and nothing it
produces predicts the outcome of any visa application. Consular requirements
change without notice and vary between consulates and individual cases.
