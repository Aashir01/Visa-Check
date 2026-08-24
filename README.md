# 🛡️ VisaGuard — Don't let a paperwork mistake cost you your trip

**VisaGuard scans your visa documents and tells you what's wrong *before* the consulate does.**

We all know the feeling — you've collected every document, checked every form twice, and still that little voice in your head whispers: *"did I forget something?"* That's exactly why we built this.

Drop your files in, and VisaGuard checks them against a real, sourced checklist for your exact destination. It spots missing documents, catches name mismatches across files, verifies your bank balance meets the threshold, checks your photo against the spec — and tells you in plain English how to fix each issue. No guessing, no fluff.

> ⚠️ **We are not immigration lawyers.** VisaGuard is a document checker. It tells you whether your paperwork matches the checklist. It does not predict visa outcomes, and it never claims to. Always confirm with your consulate or a qualified adviser.

---

## ✨ What can it actually do?

Here's the honest breakdown — no marketing speak:

| | |
|---|---|
| 🔍 **Document checklist** | Matches what you uploaded against what your visa type actually requires — and yes, requirements change depending on whether you're employed, a student, or self-employed |
| 🧠 **Name & detail matching** | Your name, date of birth, and passport number are compared across every single file. A flight ticket that spells your name differently than your passport? That's a real reason people get refused |
| 💰 **Funds check** | Reads your bank balance, converts currencies at live-ish rates, and checks it against your destination's published daily amount. Flags suspiciously large last-minute deposits |
| 📸 **Photo compliance** | Dimensions, head size in frame, background color, sharpness — measured against the official ICAO spec for your corridor |
| 📅 **Validity windows** | Is your passport valid for long enough after your return? Does your insurance cover every single day? Are your bank statements and letters still in date? |
| 🤖 **AI letter review** | Reads your invitation letters, employment letters, and cover letters for the specific details consulates look for *(optional — needs Claude or DeepSeek API key)* |
| 📊 **Risk score** | A clear 0–100 score. Severity-ranked issues. Fix instructions for each one. Branded PDF if you want it |

And here's the thing — **a free check still covers 90% of this**. The only thing that costs money is the AI reading your letters. Everything else is plain old code.

### And then there's the part nobody else does

Most tools stop at "here's your checklist". The three below are about what happens *after* — and they're the reason people come back.

| | |
|---|---|
| 🔓 **Refusal decoder** | A Schengen refusal isn't a letter — it's a form. Annex VI of the Visa Code fixes eleven numbered grounds, identical in all 29 states, and the officer just ticks boxes. Upload it and we decode which grounds you got, in plain words, **deterministically at $0.00** — matched against the official wording, not guessed at by a model. Then you get an ordered recovery plan tied to that corridor's checklist |
| 📆 **Appointment-date awareness** | A bank statement that's fine today is 46 days old at an appointment three weeks out — and it's the *appointment* date the consulate applies. Tell us when you're handing the file in and every age limit is measured against that day, with a timeline showing exactly what expires when. People assemble perfect files and submit quietly-expired documents constantly. This is the fix |
| 🔁 **Re-check with a diff** | "You still have 4 issues" is a useless thing to hear after an evening of work. Re-check and you get the delta instead — fixed / still open / new — plus, if you're recovering from a refusal, whether the **specific grounds you were refused on** are now clear. And it's free: charging again to confirm the fixes we asked for would be absurd |

The refusal loop is also how we know whether the rules are any good. Every decoded refusal is graded against the check that preceded it — which grounds we caught, which we missed. A ground the consulate cited that our check passed clean is a gap in the rules, and it's worth more than any amount of internal testing. (It's already caught one: the global Schengen pack was missing its Art. 15 insurance rules entirely.)

That grading rolls up into **`/admin/refusals`** — a per-ground scoreboard sorted worst-catch-rate-first, which is literally the work queue for the rule packs. It distinguishes a ground whose rules exist but didn't fire (tune the thresholds) from one with no rules behind it at all (write some), because those need different fixes. Every other number in the admin area measures the system against itself; this one measures it against a real consular officer.

---

## 🌍 Where does it work?

**11 corridors. 9 destinations. Any passport, any origin country.**

Planning a trip from India to Germany? UK to Spain for a holiday? USA to Japan for business? Pakistan to Saudi for Umrah? We've got you covered.

| Destination | Coverage | What you need |
|---|---|---|
| 🇪🇺 **Schengen Area** | 29 countries (France, Germany, Spain, Italy, Netherlands…) | Short-stay Type C — visa-required or visa-free depending on your passport |
| 🇬🇧 **United Kingdom** | England, Scotland, Wales, Northern Ireland | Standard Visitor — visa, ETA (£10), or nothing depending on nationality |
| 🇺🇸 **United States** | All 50 states + territories | B1/B2 or ESTA — overcome 214(b) immigrant intent presumption |
| 🇨🇦 **Canada** | All provinces & territories | TRV ($100 CAD) or eTA ($7 CAD) depending on passport |
| 🇦🇺 **Australia** | All states | Subclass 600 ($195 AUD) or ETA/eVisitor |
| 🇦🇪 **UAE** | Dubai, Abu Dhabi, Sharjah, all emirates | Tourist visa, e-Visa, or visa-on-arrival — airline-sponsored options available |
| 🇯🇵 **Japan** | All prefectures | Visa-free for 71 nationalities. Others need a visa + day-by-day itinerary |
| 🇹🇷 **Turkey** | Istanbul, Antalya, Cappadocia, all regions | e-Visa online ($20–80), visa-free for many, sticker visa for some |
| 🇸🇦 **Saudi Arabia** | Umrah pilgrimage *(Pakistan-origin)* | Licensed agent sponsorship required |

Each pack is **origin-agnostic** — it works whether you're traveling from London, Lahore, Lagos, or Lima. The checklist adjusts based on your employment status too.

---

## 🚀 Get it running (takes about 5 minutes)

Two things to start: the Python backend and the Next.js frontend. Here's the no-nonsense version:

### Step 1 — Backend

```bash
cd backend

# Make a virtual environment
# Windows:
py -3.13 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Mac / Linux:
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# The only system thing you need to install is Tesseract OCR:
# Windows →  winget install UB-Mannheim.TesseractOCR
# Mac     →  brew install tesseract
# Linux   →  sudo apt install -y tesseract-ocr

# Copy the config template and edit your secret key
cp .env.example .env

# Seed the database — creates admin account + loads all rule packs
.venv/bin/python -m app.seed --admin-email you@yoursite.com --admin-password 'pick-a-good-password'

# Quick health check — confirms OCR is actually working
.venv/bin/python cli.py doctor

# Start the server
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Your API docs are now live at **http://localhost:8000/docs** 🎉

> **Upgrading an existing dev database?** Seeding calls `Base.metadata.create_all`, which
> creates missing *tables* but silently ignores missing *columns*. A `visaguard.db` that
> predates a model change keeps working until something selects the new column, then
> returns a 500 — `no such column: checks.submission_date` is the usual first symptom.
> Delete the SQLite file and re-seed, or add the columns in place with
> `ALTER TABLE … ADD COLUMN` (they are nullable, so nothing needs backfilling). Alembic is
> the real answer and is not wired up yet.

### Step 2 — Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open **http://localhost:3000** and sign in with the admin account you just created. Done.

### Want AI-powered letter reviews?

The app works perfectly without any AI key — every deterministic check still runs. But if you want the AI to actually *read* your invitation letters and employment docs (instead of just checking they exist), pick your provider:

```env
# Claude (by Anthropic) — reliable, great quality
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# DeepSeek — equally capable, ~20x cheaper per token
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
LLM_MODEL=deepseek-chat
LLM_PRICE_IN_PER_MTOK=0.14
LLM_PRICE_OUT_PER_MTOK=0.28
```

You can set both keys at once — the system automatically uses whichever one works. And don't worry about surprise bills: every check has a hard spending cap (`$0.15` by default). Hit the cap and the pipeline gracefully degrades to deterministic-only, telling you exactly what happened.

---

## 💸 Running costs — the real numbers

A free check costs **$0.00** because it runs deterministic rules only. And honestly? That covers most of what you need.

Here's what a *full* AI check costs, measured on a real test bundle (~1,871 tokens in, ~1,500 out):

| Model | Per check | If 1,000 people use it today | If 10,000 people use it |
|---|---|---|---|
| Claude Sonnet 5 | ~$0.028 | ~$843/month | ~$8,434/month |
| Claude Haiku 4.5 | ~$0.009 | ~$281/month | ~$2,811/month |
| **DeepSeek Chat** | **~$0.004** | **~$128/month** | **~$1,280/month** |

That's the whole reason we added DeepSeek support — same quality of review, a fraction of the cost.

---

## 🎨 What does it look like?

A deep navy dark theme with one confident blue accent and a semantic risk ramp — green, amber, orange, red — that means the same thing everywhere it appears.

- **Landing page:** footage of an actual immigration counter behind the hero, with a worked example of a finished report sitting beside the headline. Then what gets checked, the four steps, the refusal decoder, all eleven corridors, pricing and an FAQ
- **Check flow:** a `Corridor → Upload → Report` stepper across all three pages, so nobody is ever guessing how much is left. The corridor you picked is shown as a photograph of the destination, not just its name
- **The report:** a 0–100 gauge in the band colour, issues grouped by severity with fix instructions, a validity timeline dated to your appointment, and an honest "checks that could not be run" list that never reads as a pass
- **Fonts:** Sora for headings, Inter for UI, JetBrains Mono for versions and IDs

Imagery and footage are Pexels-licensed and registered in one place (`frontend/lib/media.ts`) so a photo is chosen once and reused. Every picture reserves its aspect box and paints the image's dominant colour underneath, so nothing shifts as it loads and a failed CDN request leaves a plain surface rather than a hole. Autoplaying footage is skipped entirely for anyone whose OS asks for reduced motion, serves a 720p file on narrow screens, and pauses once scrolled past.

It's designed to feel like a tool you can trust — not another generic SaaS landing page.

---

## 🧪 Under the hood — how a check actually works

```
upload → OCR → classify → extract → rules → AI review → score → report
```

The clever bit is that expensive steps run *last*, on the smallest amount of data:

1. **OCR** — If your PDF was born digital (most bank statements, e-tickets, insurance docs are), we read straight from the text layer. Free and more accurate than scanning. Only actual scans and phone photos hit Tesseract
2. **Classify** — Keyword matching identifies most documents instantly. Only the tricky ones get one batched AI call for the whole bundle
3. **Extract** — Per-document-type regex extractors grab the fields we need. The passport MRZ gets special treatment — ICAO 9303 check digits let us *verify* we read it right, not just hope we did. AI fills only what regex genuinely can't find, and never overwrites a deterministic value
4. **Rules** — Your corridor's checklist gets evaluated: missing docs, mismatched names, insufficient funds, expired passports, invalid insurance dates…
5. **AI Review** — One call, only for what code can't judge. Does the invitation letter actually state who's paying? Does the employment letter confirm approved leave?
6. **Score** — 100 minus severity-weighted penalties. Clear, transparent, no black box

The whole pipeline makes **two or three AI calls per check, not one per document**. That's the difference between cents and dollars.

---

## 📋 Rule packs — the secret sauce

Rule packs are JSON files, not code. Change a threshold in `/admin/rules` and product behavior updates instantly — no deploy, no downtime.

```
backend/app/rulepacks/
  schengen_short_stay.json    ← 29 Schengen countries, per-state fund amounts
  uk_standard_visitor.json    ← UK visitor rules (Appendix V)
  usa_b1b2.json               ← US B1/B2 with 214(b) immigrant intent checks
  canada_visitor.json         ← Canada TRV with biometrics
  australia_visitor.json      ← Australia subclass 600 with GTE requirement
  uae_tourist.json            ← UAE e-visa, on-arrival, airline-sponsored
  japan_tourist.json          ← Japan (includes the unique day-by-day itinerary rule!)
  turkey_tourist.json         ← Turkey e-visa system
  schengen_short_stay_pk.json ← Schengen — Pakistan origin
  uk_visitor_pk.json          ← UK — Pakistan origin
  saudi_umrah_pk.json         ← Saudi Umrah — Pakistan origin
```

### Every rule knows where it came from

We take provenance seriously. Every document requirement and every rule declares where it comes from:

| Level | Means | Example |
|---|---|---|
| `law` | Actual statute or regulation | EU Visa Code Art. 12 — must cite the source |
| `member_state` | A country's own published figure | Spain's SMI-linked daily amount |
| `official_guidance` | Published consulate or ministry guidance | "Most consulates expect a cover letter" |
| `heuristic` | **Our best guess — clearly labeled** | "£100/day seems reasonable for UK visits" |

The validator won't let you save a pack that claims something is `law` without a source citation. Nothing is presented as official unless we can point to exactly where it's written.

### Rule types at a glance

| Rule | What it catches in the real world |
|---|---|
| Name consistency | Bank statement says "Ahmad R Khann" but passport says "Ahmed Raza Khan" |
| Passport validity | Expiring 2 months after your trip? Not enough blank pages? Issued 11 years ago? |
| Financial sufficiency | Your balance after currency conversion vs what Spain actually requires per day |
| Statement recency | Bank statement from 45 days ago? Too old |
| Sudden deposit | One deposit that's 30% of your total balance appears right before applying |
| Insurance coverage | Policy doesn't cover the last day of your trip, or is below the €30,000 minimum |
| Photo spec | Wrong size, wrong background, too old, or head takes up too much of the frame |

---

## 🔒 How we handle your documents

We treat your passport scan and bank statements like what they are — extremely sensitive personal documents:

- **Encrypted at rest** using Fernet (key comes from your `SECRET_KEY`)
- **Never stored as plaintext** — decryption happens in a short-lived temp file only while being read
- **Auto-deleted after 30 days** — reports survive, source documents don't
- **Deleting a check** wipes its files immediately, no waiting period

Run a daily cron job to clean up: `python cli.py purge`

---

## 🛡️ Keeping the bad guys out

A free document upload endpoint is catnip for bots. Every limit below is configurable and enforced per-process:

| Limit | Default | Why |
|---|---|---|
| Checks per account per day | 20 | Stops one person hammering the system |
| Checks per IP per hour | 10 | Catches unauthenticated abuse |
| Upload requests per IP per hour | 120 | Lets legitimate multi-file uploads through, blocks scrapers |
| Login attempts per IP per hour | 20 | Basic brute-force protection |
| Max upload bundle size | 60 MB | Keeps storage costs predictable |

---

## 🖥️ The CLI — for power users

Before there was a web UI, there was a command line. It's still the best way to test rule packs against real bundles:

```bash
cd backend

# What corridors do I have?
python cli.py corridors

# Run a complete check from the terminal
python cli.py check \
    --corridor schengen_short_stay \
    --profile employed \
    --from 2026-09-10 --to 2026-09-20 \
    --pdf report.pdf --json result.json \
    ./my-documents-folder/

# Decode a folder of past refusal letters at once
python cli.py refusal ./past-refusals/ --corridor schengen_short_stay --verbose

# Or just name the grounds off the form yourself
python cli.py refusal --codes 3,7 --corridor schengen_short_stay

# Generate fake test documents (no real data needed)
python tests/make_fixtures.py --out /tmp/clean --case clean
python tests/make_fixtures.py --out /tmp/bad   --case problems

# Is your OCR actually working? Run the doctor
python cli.py doctor

# Clean up old files
python cli.py purge
```

The `check` command exits with code `2` when it finds critical issues — pipe it into your scripts, run it over folders of old cases, automate your testing.

`refusal` is the other half of that workflow. Point it at a folder of past refusal letters and it prints, for each one, the grounds given, the verdict, and (with `--verbose`) which rules in your packs actually cover each ground. The summary at the end is the number worth watching: **how many grounds came up that no rule covers**. That's your list of rules to write, derived from your own casework rather than from guessing.

---

## 🧪 Tests

```bash
cd backend && .venv/bin/python -m pytest -q     # 224 tests and counting
cd frontend && npx tsc --noEmit && npm run build
```

The test suite covers MRZ check digits, name matching, money and date parsing, currency conversion, every rule outcome (including "could not evaluate"), scoring, pack validation, LLM budget enforcement, rate limiting, refusal-ground decoding and recovery plans, submission-date timelines, re-check diffs, the free-re-check limits, and a specific guard that stops the AI from hallucinating a finding into your report.

Four of them drive a real Tesseract binary against a photographed passport. If `cli.py doctor` says OCR is not working, those four fail with empty OCR output — fix the install rather than the test.

---

## ⚠️ Important — the packs are drafts

All rule packs are thoroughly researched against official sources — EU Visa Code, UKVI Appendix V, US State Department guidance, IRCC rules, Australian Home Affairs, Japan MOFA, and more. But they're marked `unverified: true` for a reason.

**Sourced doesn't mean verified.** Requirements change. Consulates interpret rules differently. The only way to close that gap is real casework. Before you charge anyone money:

- Go through each pack in `/admin/rules` and correct it from your own experience
- Re-check Schengen per-state amounts and Spain's SMI every January
- Run 20 past refusal cases through the CLI — if fewer than 15 get caught, fix your rules
- Swap out the UK funds heuristic for a number backed by your own refusal data
- Set `unverified: false` only when a pack has earned it

---

## 📁 How everything is organized

```
backend/
  app/
    pipeline/     OCR, MRZ parsing, classification, extraction, rules engine,
                  qualitative review, scoring, submission-date timeline,
                  re-check diffs, multi-provider LLM (Claude + DeepSeek)
    refusal/      The eleven Annex VI grounds, deterministic decoding of a
                  refusal letter, and the recovery plan built from it
    rulepacks/    11 corridor packs (8 global + 3 Pakistan-origin)
    api/          Auth, corridors, checks, refusals, admin dashboard
  cli.py          Command-line runner for checks, doctor, purge
frontend/
  app/            Landing page, auth, check flow, reports, refusal decoding
                  and recovery plans, account, admin
  components/     UI primitives, one icon set, media (photo + ambient video),
                  page headers with breadcrumbs and the check stepper,
                  original SVG illustrations
  lib/            API client, auth context, formatting, media registry
```

---

## 🚧 What we haven't built yet

- **Billing integration.** Credits and tiers are tracked and enforced, but there's no Stripe or Paddle connected yet. The code is ready — the merchant account isn't
- Cover letter generation and non-English report output — still on the v2 roadmap
- **The refusal decoder is Schengen-only.** It rests on Annex VI being a standardised form; the UK, US and others give free-prose refusals with no fixed grounds, so those fall through to the AI path and are much less reliable
- Anonymous checks require an account. It's a deliberate trade-off: slightly more friction at signup, but every user is attributable
- **Database migrations.** Schema changes are applied by `create_all`, which adds tables but never columns. Fine while the only database is a dev SQLite file you can delete; not fine the first time there is data worth keeping. Alembic before the first paying user

---

## 🙏 Built by

**[Aashir Noman](https://github.com/Aashir01)** — with a lot of coffee and an unhealthy obsession with visa checklists.

**Important legal bit:** VisaGuard is a document completeness checker. It is not an immigration adviser, lawyer, or consular officer. It tells you whether your documents match a specific, named, versioned checklist on a specific date. It does not give legal advice, it does not predict visa outcomes, and it never claims to. Consular requirements change without notice and vary between individual consulates and cases. Always confirm requirements directly with the relevant consulate or a qualified immigration professional.
