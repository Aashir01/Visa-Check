# VisaGuard

**Nearly half of Pakistani visa applications are refused. Most of them fail on paperwork.**

VisaGuard reads an applicant's document set and finds what will sink it — the
missing paper, the name spelled differently on the ticket, the bank statement
three days too old — before it reaches the consulate. Sixty seconds, and a
report the applicant can act on.

---

## The problem

A refusal costs far more than the fee. The fee is non-refundable, so is the
appointment, often so are the flights — and a refusal stamp makes the next
application harder, which is why families apply again and lose again.

| | |
|---|---|
| **46%** | of Pakistani Schengen applications refused in 2025 (62% in 2024) |
| **112,387** | UK and Schengen applications from Pakistan rejected in one year |
| **Rs 4.56 billion** | lost in non-refundable fees by Pakistani applicants in 2025 (≈ USD 16m) |
| **2 million+** | Pakistanis perform Umrah each year, all through licensed agents |

> Almost none of these files fail because the applicant was ineligible. They
> fail because the paperwork was incomplete, inconsistent, or out of date.

A consular officer spends a few minutes on a file. They are not looking for
reasons to approve — they are checking whether the file holds together. A name
reading `AHMAD R KHANN` on the bank statement and `AHMED RAZA KHAN` in the
passport is enough to lose the benefit of the doubt. So is insurance that ends
a day before the return flight.

These are not judgement calls. They are checkable facts. Nobody was checking them.

---

## What it does

**1. Reads every document.** Passports, bank statements, tickets, insurance,
letters, photos — PDF or a photo taken on a phone. It works out what each file
is without being told.

**2. Pulls out the facts.** Name, date of birth, passport number, balances,
policy dates, coverage amounts. Passport identity comes from the machine-readable
zone, where check digits prove the read was correct rather than merely plausible.

**3. Checks them against the live checklist.** Every requirement for that exact
country, visa type and applicant situation — employed, self-employed, student or
retired.

**4. Says what to fix.** A risk score, issues ranked critical to minor, the
evidence behind each one, and plain-language instructions. Downloadable as a PDF
the agency can hand to its client.

**5. Dates it against the day that counts.** Not today — the appointment. A
statement that is 25 days old now is 46 days old at a slot three weeks out, and
it is the appointment date the consulate applies. The report carries a timeline
of what expires when, measured against that day.

**6. Decodes the refusal, if one comes.** And turns it into the next attempt.

### The part nobody else has built

A Schengen refusal is not a letter. Annex VI of the Visa Code fixes a single
standard form with eleven numbered grounds, identical across all 29 member
states, and the officer ticks boxes. That makes a refusal **machine-decodable** —
the reason is a number, not prose.

Almost nobody exploits this. Applicants receive the form and cannot read it;
"ground 3" means nothing to someone who has just lost their fee and their slot.

VisaGuard decodes it — against the official wording, deterministically, at
**$0.00 per decode** — and returns:

- which grounds were given, in plain words
- whether reapplying can actually answer them, or whether the honest advice is
  to appeal instead
- an ordered plan tied to that corridor's checklist
- a targeted re-check that reports, ground by ground, whether the specific things
  cited are now clear

That last loop is also the compounding asset. Every decoded refusal is graded
against the check that preceded it — which grounds we caught, which we missed.
A ground the consulate cited that our check passed clean is a hole in the rules,
and it is worth more than any amount of internal QA. **It has already found one:**
the global Schengen pack was missing its Article 15 insurance rules entirely, so
a €15,000 policy with no repatriation cover was passing as "insurance provided".
A real refusal on ground 7 surfaced it in one pass.

No competitor has this feedback loop, because no competitor sees refusals.

### Caught in testing

- Insurance €15,000 where €30,000 is required by law
- Cover ending five days before the return flight
- Passport expiring 20 days after return, not 90
- Name mismatch between passport and bank statement
- Statement covering 1.9 months where 6 are expected
- A single deposit making up 76% of the closing balance
- Photo at the wrong ratio, too small, and too dark

### What it will never say

That you are approved. That you are eligible. That a visa is likely.

No tool can know those things. VisaGuard reports whether a document set matches
a named checklist, at a stated version, on a stated date — and says so on every
report. That restraint is the reason an agency can put its own logo on the output.

---

## For visa consultancies and travel agents

**We sell you a profit centre, not a cost.**

You already check these files by hand. Forty documents across fifteen clients,
at eleven at night, is exactly where the small mistakes get through — and your
reputation is what pays for them.

VisaGuard checks a client's whole bundle in about a minute and gives you a
branded PDF report. On the Agency plan and above, that report carries **your**
logo, not ours.

Agents already charge PKR 2,000–5,000 for a document review. Now you can deliver
it in minutes instead of an evening, with a written report the client can hold —
and the review costs you a few rupees.

| Plan | Price | What you get |
|---|---|---|
| **Starter** | $29/month | 25 checks. For a one-person consultancy. |
| **Agency** | $79/month | 150 checks, team seats, your logo on every report. |
| **White-label** | $199/month | Your branding throughout, plus custom checklist packs. |

**The arithmetic that matters.** At $79/month you get 150 checks — about PKR 150
per check. Resold inside a review you already charge PKR 2,000–5,000 for, the
subscription pays for itself on the second client of the month.

### Why not the software you already have?

Immigration CRMs cost $99–500 per user per month and *track* documents — who sent
what, what is still outstanding. Not one of them *verifies* the contents. They
will happily mark a bank statement as received when it is four months out of date
and in the wrong name.

That gap is the entire product.

---

## For applicants

**Check it yourself before you pay the fee.**

You will spend PKR 15,000 or more on the fee alone, and it does not come back.
The checklist for your country and situation is free — so is a full check of your
documents against every rule we can compute without a human reading them.

| | Free | Full check — $12 once |
|---|---|---|
| Complete checklist for your corridor | ✓ | ✓ |
| Missing documents, for your profile | ✓ | ✓ |
| Name / DOB / passport-number consistency | ✓ | ✓ |
| Funds against the threshold | ✓ | ✓ |
| Passport and insurance validity | ✓ | ✓ |
| Photo compliance | ✓ | ✓ |
| AI review of your letters | — | ✓ |
| Downloadable PDF report | — | ✓ |

Your documents are encrypted the moment they arrive, deleted automatically after
30 days, and never used to train models. Passports and bank statements are not
something to be casual about.

---

## For investors

**A vertical wedge with a maintenance moat.**

The AI is not the defensible part. Anyone can call a model. Almost nobody will
maintain accurate, versioned, per-corridor visa requirements — and that is what
the product actually is.

### Why now, and why here

Refusal rates from Pakistan sit near 46% and rose above 62% in 2024. The money
already burned on failed applications — Rs 4.56 billion in a single year — is
larger than the entire revenue this product needs to be a success. We are asking
applicants to spend a fraction of a fee they are already losing.

### The market is enumerable, not estimated

Pakistani pilgrims are **legally required** to book Umrah through a MORA-approved
operator. There are roughly **113 of them**, and they collectively handle over
two million pilgrims a year. That is not a TAM slide — it is a list of company
names, and every one is a compliance-driven buyer with volume. The Schengen and
UK consultancy market sits on top of that.

### Unit economics, measured rather than projected

The pipeline is built so the free tier makes **no model calls at all**.
Everything countable — documents, names, dates, balances, pixels — is computed in
code. Only the reading of free-text letters costs tokens.

| Tier | Revenue | AI cost | Gross margin |
|---|---|---|---|
| Free check | $0.00 | $0.0000 | n/a — costs only CPU |
| Single full check | $12.00 | $0.028 | 99.8% |
| Starter, 25 checks | $29.00 | $0.70 | 97.6% |
| Agency, 150 checks | $79.00 | $4.20 | 94.7% |

Measured on a nine-document bundle at ~1,871 input and 1,500 output tokens per
full check. Hosting and payment fees not included. A hard per-check budget is
enforced in code, so a runaway file degrades to the free checks rather than
eating the margin.

### The moat is maintenance, and it compounds

Requirements change without notice and differ by consulate. Schengen funds
thresholds alone run from €34/day in the Netherlands to €122.10/day in Spain — a
factor of three that a generic tool gets wrong in both directions.

Every rule is versioned, carries its source, and declares whether it is law, a
published state figure, official guidance, or our own calibration. Published rule
packs are immutable, and every report records the version it ran against —
correcting a rule can never rewrite an old report, which is what makes the output
safe to resell.

Low-confidence checks route to a review queue. Every correction an operator makes
becomes evaluation data. Accuracy improves with volume, and the corrections live
in the rule packs, not the model.

### Founder advantage

The operator runs a live visa and immigration consultancy with active Schengen
casework. That is customer zero, the distribution channel, and — most importantly
— the casework that verifies the rules. The hardest input to this business is
already in the building.

### The expansion path

The engine is corridor-agnostic. Adding a corridor is authoring data, not writing
software. Three corridors from Pakistan becomes N corridors from M origin
countries, and the same architecture — read a document set, check it against
versioned rules, explain the gaps — applies to any document-compliance problem
where a deadline meets a pass/fail outcome.

---

## Where it actually stands

Anything below that is not true would come out in a week of diligence or a month
of use. Here it is up front.

**Working today**

- Full pipeline: upload, read, classify, extract, check, score, report
- Three corridors — Schengen, UK visitor, Saudi Umrah
- Applicant and agency web app, branded PDF reports
- Admin console with a versioned rules editor and cost dashboard
- Free tier that provably costs nothing per check
- Refusal decoder, recovery plans, appointment-date timelines and re-check diffs —
  all verified end to end against the running API
- 208 automated tests; encryption at rest and 30-day deletion

**Not there yet**

- No paying customers. No revenue. No live traction.
- Payments are not connected — credits are enforced, checkout is not built
- Rule packs are researched and sourced, but not yet verified against real casework
- Accuracy on phone photographs of documents needs measuring on real user files
- The refusal decoder is exact for Schengen only. It works because Annex VI is a
  standardised form; the UK and US refuse in free prose with no fixed grounds, so
  those fall back to a model and are correspondingly less reliable

**The honest gap.** The rules are drawn from the EU Visa Code, UK Immigration
Rules and Saudi ministry guidance, and every report carries a visible notice that
the checklist is unverified. Turning *sourced* into *verified* takes running past
cases — including refused ones — through the tool and correcting what it misses.
That is the next piece of work, and the piece only the operator can do.

---

## The ask

**If you run a consultancy:** bring five recent files — ideally including one
that was refused — and run them through. If it does not find something you
missed, it is not worth your money and we should both know that in an afternoon.
Bring the refusal letter too: decoding it takes seconds and costs nothing, and it
tells you as much about the tool as it does about the case.

**If you are considering backing it:** the near-term plan is not a venture-scale
curve. It is 100 agencies at $79 a month, roughly $7,900 in recurring revenue,
from a market small enough to name every buyer. The interesting question is what
happens when the same engine is pointed at the next corridor, and the one after.

---

*VisaGuard is not an immigration adviser. It reports whether a document set
matches a named checklist at a stated version and date. It does not give legal or
eligibility advice, and nothing it produces predicts the outcome of any
application. Consular requirements change without notice and vary between
consulates and individual cases.*

*Refusal and volume figures: Schengen and UKVI statistics for 2025 as reported in
Pakistani press, and Pakistan's Ministry of Religious Affairs operator register.
Unit economics measured directly from the running pipeline.*
