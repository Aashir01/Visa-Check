"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  AlertIcon,
  CalendarIcon,
  ChartIcon,
  CheckCircleIcon,
  CheckIcon,
  ChevronDownIcon,
  ClockIcon,
  FormIcon,
  GlobeIcon,
  LockIcon,
  PassportIcon,
  RepeatIcon,
  ScanIcon,
  ShieldIcon,
  SparkleIcon,
  UploadIcon,
  XCircleIcon,
} from "@/components/icons";
import { GlobeIllustration, RefusalFormIllustration } from "@/components/illustrations";
import { AmbientVideo, MediaScrim, Picture } from "@/components/media";
import { Reveal } from "@/components/reveal";
import {
  Alert,
  Badge,
  Card,
  Chip,
  LinkButton,
  ScoreGauge,
  SectionHeading,
  Skeleton,
  Stat,
} from "@/components/ui";
import { api } from "@/lib/api";
import {
  CLIP_IMMIGRATION_DESK,
  CLIP_PAPERWORK,
  PHOTO_PASSPORTS_WINDOW,
  PHOTO_PASSPORT_STAMPS,
  PHOTO_VISA_PAGE,
  corridorPhoto,
} from "@/lib/media";
import type { Corridor } from "@/lib/types";

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------

const TRUST_STATS = [
  { value: "11", label: "corridors covered", hint: "across 9 destinations" },
  { value: "$0.00", label: "for a full deterministic check", hint: "AI review is the only paid part" },
  { value: "30 days", label: "then source documents are purged", hint: "encrypted the whole time" },
];

const WHAT_WE_CHECK = [
  {
    icon: CheckCircleIcon,
    title: "Document checklist",
    desc: "Matched against what your visa type actually requires — and the requirements shift depending on whether you are employed, a student, self-employed or retired.",
  },
  {
    icon: PassportIcon,
    title: "Name and detail matching",
    desc: "Your name, date of birth and passport number, compared across every file. A ticket that spells your name differently from your passport is a real refusal reason.",
  },
  {
    icon: ChartIcon,
    title: "Funds",
    desc: "Reads the balance, converts currency, and checks it against your destination's published daily amount. Flags a suspiciously large last-minute deposit.",
  },
  {
    icon: ScanIcon,
    title: "Photo compliance",
    desc: "Dimensions, head size in frame, background colour and sharpness, measured against the ICAO spec that applies to your corridor.",
  },
  {
    icon: CalendarIcon,
    title: "Validity windows",
    desc: "Is the passport valid long enough past your return? Does the insurance cover every day? Are the statements and letters still in date on the day you hand them in?",
  },
  {
    icon: SparkleIcon,
    title: "AI letter review",
    desc: "Invitation, employment and cover letters read for the specific details consulates look for — not merely confirmed to exist. The one part that costs money.",
  },
];

const FEATURE_CARDS = [
  {
    title: "A checklist that cites its sources",
    tag: "Free",
    desc: "Every corridor's requirements are pinned to published sources at a stated version and date, then adjusted for your employment situation.",
    href: "/check/new",
    photo: PHOTO_PASSPORT_STAMPS,
  },
  {
    title: "AI that actually reads the letters",
    tag: "Optional AI",
    desc: "Invitation letters, employment letters, cover letters — read for the details a consular officer looks for, rather than ticked off as present.",
    href: "/check/new",
    photo: PHOTO_PASSPORTS_WINDOW,
  },
  {
    title: "Dated to your appointment day",
    tag: "Free",
    desc: "A statement that is fine today can be stale by your slot. Every age limit is measured against the day you hand the file in, with a timeline of what expires when.",
    href: "/check/new",
    photo: PHOTO_VISA_PAGE,
  },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Pick your corridor",
    desc: "Destination, your situation, travel dates and the day of your appointment. The checklist appears before you upload anything.",
    icon: GlobeIcon,
  },
  {
    step: "02",
    title: "Upload the bundle",
    desc: "PDFs or photos, in any order. Document types are detected for you, and everything is encrypted the moment it arrives.",
    icon: UploadIcon,
  },
  {
    step: "03",
    title: "The rules run",
    desc: "Checklist, identity, funds, dates and photo rules evaluate in seconds. The AI letter review runs only if your check includes it.",
    icon: ScanIcon,
  },
  {
    step: "04",
    title: "Fix, then re-check",
    desc: "A 0–100 score with severity-ranked issues and fix instructions. Re-checking shows the delta — fixed, still open, new — and costs nothing.",
    icon: RepeatIcon,
  },
];

const AFTER_REFUSAL = [
  {
    icon: FormIcon,
    title: "The grounds, decoded",
    desc: "Which of the eleven you were given, what each one says about your file, and which documents it points at.",
  },
  {
    icon: CalendarIcon,
    title: "Dated to your appointment",
    desc: "A bank statement that is fine today can be six weeks stale by your slot. Every document is dated against the day you hand it in, because that is the date the consulate applies.",
  },
  {
    icon: RepeatIcon,
    title: "Re-check, ground by ground",
    desc: "Rebuild the file and we report what you fixed, what is still open, and whether the grounds you were refused on are now clear. Free — confirming a fix should not cost another check.",
  },
];

// Mirrors the plans the backend actually recognises — free, starter, agency,
// white_label. Inventing a price on the landing page that no plan implements
// is the sort of thing that only shows up after someone tries to buy it.
const PRICING = [
  {
    name: "Free",
    price: "$0",
    cadence: "",
    lede: "The whole checklist, every deterministic rule, and one full AI check to try it.",
    features: [
      "Complete document checklist for your corridor",
      "Identity, funds, dates and photo rules",
      "One full AI analysis included",
      "Refusal decoding, always free",
    ],
    cta: { label: "Start free", href: "/check/new", variant: "secondary" as const },
    featured: false,
  },
  {
    name: "Starter",
    price: "$29",
    cadence: "/month",
    lede: "For someone working through their own application, or one or two a month.",
    features: [
      "25 checks per month",
      "AI review of invitation, employment and cover letters",
      "PDF report",
      "Free re-checks with a fixed / still-open diff",
    ],
    cta: { label: "Get started", href: "/register", variant: "primary" as const },
    featured: true,
  },
  {
    name: "Agency",
    price: "$79",
    cadence: "/month",
    lede: "For consultancies running files for several applicants at once.",
    features: [
      "150 checks per month",
      "Team seats — everyone sees every check",
      "Shared credit pool",
      "Priority support",
    ],
    cta: { label: "Get started", href: "/register", variant: "neon" as const },
    featured: false,
  },
  {
    name: "White-label",
    price: "$199",
    cadence: "/month",
    lede: "Reports that go out under your own name rather than ours.",
    features: [
      "Everything in Agency",
      "Your logo, name and colour on every report",
      "Higher check volume",
      "Priority support",
    ],
    cta: { label: "Talk to us", href: "/register", variant: "secondary" as const },
    featured: false,
  },
];

const FAQ = [
  {
    q: "Is this immigration advice?",
    a: "No. VisaGuard is a document completeness checker. It reports whether your documents match a named checklist at a stated version and date. It does not assess your eligibility, and nothing it produces predicts the outcome of an application. For advice about your circumstances, speak to a qualified adviser or the consulate.",
  },
  {
    q: "What does the free check actually include?",
    a: "Every deterministic rule: the checklist itself, name and detail matching across files, the funds calculation, all the validity windows, and photo compliance. That is roughly ninety per cent of what the tool does. The only paid part is the AI reading the content of your letters.",
  },
  {
    q: "What happens to my documents?",
    a: "They are encrypted the moment they arrive and are never stored as plaintext — decryption happens in a short-lived temporary file only while a rule is reading them. Source documents are deleted automatically after thirty days; the report survives, the files do not. Deleting a check wipes its files immediately. Nothing is used to train models.",
  },
  {
    q: "Why does the appointment date matter so much?",
    a: "Because it is the date the consulate applies, not today's date. A bank statement issued today is forty-six days old at an appointment three weeks out, and plenty of documents have an age limit shorter than that. Tell us when you are handing the file in and every limit is measured against that day, with a timeline showing what expires when.",
  },
  {
    q: "How does refusal decoding work?",
    a: "A Schengen refusal is not a letter — it is a form. Annex VI of the Visa Code fixes eleven numbered grounds, identical across all twenty-nine member states, and the officer ticks boxes. We match your form against the official wording rather than asking a model to guess, so most letters decode exactly. It costs nothing.",
  },
  {
    q: "Does a re-check cost another credit?",
    a: "No. Charging again to confirm the fixes we asked for would be absurd. A re-check reports the delta — what you fixed, what is still open, what is new — and if you are recovering from a refusal, whether the specific grounds you were cited on are now clear.",
  },
];

// ---------------------------------------------------------------------------
// The sample report
//
// The old landing page showed a mock dashboard with an upload zone and a score
// of 23, unlabelled — which reads as a live check that has somehow already
// analysed documents nobody uploaded. It is presented here as what it is: a
// worked example, captioned as such, so the product is legible without the
// page pretending to be signed in.
// ---------------------------------------------------------------------------

const SAMPLE_FINDINGS = [
  {
    severity: "critical" as const,
    title: "Travel insurance does not cover the whole trip",
    detail: "Cover ends 12 Mar, one day before your return flight on 13 Mar.",
  },
  {
    severity: "critical" as const,
    title: "Name mismatch between passport and flight booking",
    detail: "Passport reads AHMED KHAN; the booking reads AHMAD KHAN.",
  },
  {
    severity: "warning" as const,
    title: "Bank statement will be 41 days old at your appointment",
    detail: "This corridor accepts statements up to 30 days old on the day of submission.",
  },
  {
    severity: "warning" as const,
    title: "Large deposit nine days before applying",
    detail: "€4,200 credited on 2 Feb with no matching salary entry. Add evidence of source.",
  },
  {
    severity: "info" as const,
    title: "Cover letter does not state your return intent",
    detail: "Optional, but it is the first thing this consulate looks for.",
  },
];

const SEVERITY_UI = {
  critical: { icon: XCircleIcon, chip: "border-critical/30 bg-critical/10 text-critical", label: "Critical" },
  warning: { icon: AlertIcon, chip: "border-warn/30 bg-warn/10 text-warn", label: "Warning" },
  info: { icon: CheckCircleIcon, chip: "border-neon-500/30 bg-neon-500/10 text-neon-300", label: "Info" },
};

function SampleReport() {
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface-elevated px-5 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-2 w-2 rounded-full bg-good" />
          <span className="text-sm font-semibold text-ink">Schengen — short stay</span>
          <Chip className="font-mono text-[11px]">checklist v2.1.0</Chip>
        </div>
        <span className="text-xs text-muted">Worked example</span>
      </div>

      <div className="grid gap-6 p-5 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center sm:gap-8 sm:p-6">
        <div className="flex justify-center">
          <ScoreGauge score={58} band="elevated" size={150} />
        </div>
        <div>
          <p className="eyebrow">Rejection risk — elevated</p>
          <p className="mt-2 text-[15px] leading-relaxed text-muted">
            Two issues would very likely stop this file at the counter, and both take under
            an hour to fix. The score moves to <span className="font-semibold text-good">91</span>{" "}
            once they are resolved.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge className="border-critical/30 bg-critical/10 text-critical">2 critical</Badge>
            <Badge className="border-warn/30 bg-warn/10 text-warn">2 warnings</Badge>
            <Badge className="border-line bg-surface-hover text-muted">1 note</Badge>
          </div>
        </div>
      </div>

      <ul className="divide-y divide-line border-t border-line">
        {SAMPLE_FINDINGS.map((f) => {
          const ui = SEVERITY_UI[f.severity];
          const Icon = ui.icon;
          return (
            <li key={f.title} className="flex gap-3.5 px-5 py-4 transition-colors hover:bg-surface-hover/60">
              <span
                className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${ui.chip}`}
              >
                <Icon className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-ink">{f.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{f.detail}</p>
              </div>
            </li>
          );
        })}
      </ul>

      <div className="border-t border-line bg-surface-elevated px-5 py-3.5">
        <p className="text-xs leading-relaxed text-muted">
          Illustrative figures. Your report is built from your own documents and your
          corridor&rsquo;s current rule pack.
        </p>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function LandingPage() {
  const [corridors, setCorridors] = useState<Corridor[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .corridors()
      .then(setCorridors)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div>
      {/* =================================================================
          HERO
          ================================================================= */}
      <section className="relative isolate overflow-hidden">
        <AmbientVideo clip={CLIP_IMMIGRATION_DESK} />
        <MediaScrim direction="left" />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-grid opacity-30 mask-radial"
        />

        {/* The header floats over this, so the top padding clears it. */}
        <div className="container-page relative grid gap-14 pb-20 pt-16 sm:pt-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)] lg:items-center lg:gap-12 lg:pb-28 lg:pt-24">
          <div className="animate-slide-up">
            <Badge className="border-neon-500/30 bg-neon-500/10 text-neon-300 backdrop-blur">
              <SparkleIcon className="h-3.5 w-3.5" />
              Checked against a versioned, sourced checklist
            </Badge>

            <h1 className="mt-6 max-w-[15ch] font-display text-display-lg font-bold text-white [text-wrap:pretty] sm:max-w-none">
              Find the problem in your visa file{" "}
              <span className="text-gradient">before the consulate does.</span>
            </h1>

            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-slate-300">
              Upload your application bundle and get a rejection-risk report in under a minute
              — missing documents, name mismatches, funds, expiry dates and photo spec, all
              measured against the published requirements for your corridor.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <LinkButton href="/check/new" variant="primary" size="lg">
                Run a free check
                <span aria-hidden>→</span>
              </LinkButton>
              <LinkButton href="/refusals/new" variant="onMedia" size="lg">
                Decode a refusal
              </LinkButton>
            </div>

            <p className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <CheckIcon className="h-3.5 w-3.5 text-good" /> No card required
              </span>
              <span className="flex items-center gap-1.5">
                <LockIcon className="h-3.5 w-3.5 text-good" /> Encrypted at rest
              </span>
              <span className="flex items-center gap-1.5">
                <ClockIcon className="h-3.5 w-3.5 text-good" /> Deleted after 30 days
              </span>
            </p>

            <div className="mt-12 grid gap-6 border-t border-white/10 pt-8 sm:grid-cols-3">
              {TRUST_STATS.map((s) => (
                <Stat key={s.label} value={s.value} label={s.label} hint={s.hint} />
              ))}
            </div>
          </div>

          {/* The report is the product, so it is what the hero shows. */}
          <div className="animate-slide-up lg:pl-4" style={{ animationDelay: "120ms" }}>
            <div className="rounded-[26px] border border-white/10 bg-surface/70 p-2 shadow-overlay backdrop-blur-xl">
              <SampleReport />
            </div>
          </div>
        </div>
      </section>

      {/* =================================================================
          WHAT GETS CHECKED
          ================================================================= */}
      <section id="checks" className="section border-t border-line">
        <div className="container-page">
          <SectionHeading
            eyebrow="Everything, checked"
            title="Your paperwork, read the way a consular officer reads it."
            lede="The deterministic rules run instantly and cost nothing. The AI steps in only where a document has to actually be read."
          />

          <div className="mt-12 grid gap-x-8 gap-y-9 sm:grid-cols-2 lg:grid-cols-3">
            {WHAT_WE_CHECK.map((item, i) => (
              <Reveal key={item.title} delay={i * 60}>
                <div className="flex gap-4">
                  <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-neon-500/20 bg-neon-500/10 text-neon-400">
                    <item.icon className="h-5 w-5" />
                  </span>
                  <div>
                    <h3 className="font-display text-base font-semibold text-ink">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">{item.desc}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {FEATURE_CARDS.map((f, i) => (
              <Reveal key={f.title} delay={i * 80} className="h-full">
                <Link href={f.href} className="group block h-full">
                  <Card variant="interactive" className="flex h-full flex-col overflow-hidden">
                    <Picture
                      photo={f.photo}
                      ratio="16/10"
                      sizes="(min-width: 768px) 33vw, 100vw"
                      imgClassName="transition-transform duration-[900ms] ease-out group-hover:scale-[1.07]"
                    >
                      <div
                        aria-hidden
                        className="absolute inset-0 bg-gradient-to-t from-surface-card via-surface-card/25 to-transparent"
                      />
                      <span className="absolute bottom-3.5 left-4 rounded-full bg-neon-600 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-white shadow-glow-sm">
                        {f.tag}
                      </span>
                    </Picture>
                    <div className="flex flex-1 flex-col p-5">
                      <h3 className="font-display text-lg font-semibold text-ink">{f.title}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-muted">{f.desc}</p>
                      <p className="mt-auto pt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-neon-400">
                        See the checklist
                        <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
                      </p>
                    </div>
                  </Card>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* =================================================================
          HOW IT WORKS
          ================================================================= */}
      <section id="how" className="relative isolate overflow-hidden border-y border-line">
        <AmbientVideo clip={CLIP_PAPERWORK} kenburns={false} />
        <MediaScrim direction="full" />

        <div className="container-page relative section">
          <SectionHeading
            eyebrow="Four steps"
            title="From a folder of scans to a submission-ready file."
            lede="Most people finish in one sitting. The longest part is finding the documents, not checking them."
            align="center"
          />

          <ol className="mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {HOW_IT_WORKS.map((item, i) => (
              <Reveal key={item.step} delay={i * 90} as="li" className="h-full">
                <Card className="relative h-full overflow-hidden bg-surface-card/85 p-6 backdrop-blur">
                  <span
                    aria-hidden
                    className="pointer-events-none absolute -right-3 -top-5 font-display text-7xl font-bold text-white/[0.045]"
                  >
                    {item.step}
                  </span>
                  <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-neon-500/25 bg-neon-500/10 text-neon-400">
                    <item.icon className="h-6 w-6" />
                  </span>
                  <h3 className="mt-5 font-display text-base font-semibold text-ink">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{item.desc}</p>
                </Card>
              </Reveal>
            ))}
          </ol>

          <div className="mt-12 flex justify-center">
            <LinkButton href="/check/new" variant="primary" size="lg">
              Start with your corridor
              <span aria-hidden>→</span>
            </LinkButton>
          </div>
        </div>
      </section>

      {/* =================================================================
          AFTER A REFUSAL

          The differentiator, and the reason people come back. Every other
          tool stops at "here is your checklist"; this is about the moment
          someone has already lost their fee.
          ================================================================= */}
      <section id="refusals" className="section">
        <div className="container-page grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,430px)] lg:items-start">
          <div>
            <SectionHeading
              eyebrow="Already been refused?"
              title={
                <>
                  A Schengen refusal is not a letter.
                  <br />
                  <span className="text-neon-400">It is a form.</span>
                </>
              }
              lede="Annex VI of the Visa Code fixes one standard refusal form with eleven numbered grounds, identical in all twenty-nine member states. The officer ticks boxes. That means the reason you were refused is a number — and a number can be read."
            />

            <p className="mt-5 max-w-xl leading-relaxed text-muted">
              Upload the form and we will tell you which grounds you were given in plain words,
              whether reapplying can actually answer them, and what to change first. We match
              against the official wording rather than guessing, so most letters decode exactly
              — and it costs nothing.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <LinkButton href="/refusals/new" variant="primary" size="lg">
                Decode my refusal — free
              </LinkButton>
              <LinkButton href="/check/new" variant="secondary" size="lg">
                Check a file before submitting
              </LinkButton>
            </div>

            <div className="mt-8 max-w-xl">
              <Alert tone="info">
                Some grounds cannot be answered with better paperwork at all. When yours is one
                of them we say so and point you at appealing, rather than selling you a re-check
                that cannot help.
              </Alert>
            </div>
          </div>

          <div className="space-y-4">
            {/* The point of the section, drawn: eleven numbered boxes and a
                tick. Original artwork rather than a photograph, because no
                stock library has a picture of Annex VI. */}
            <Card className="overflow-hidden bg-surface-elevated">
              <RefusalFormIllustration className="w-full" />
            </Card>

            {AFTER_REFUSAL.map((item, i) => (
              <Reveal key={item.title} delay={i * 80}>
                <Card className="p-5">
                  <div className="flex items-start gap-4">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-neon-500/20 bg-neon-500/10 text-neon-400">
                      <item.icon className="h-5 w-5" />
                    </span>
                    <div>
                      <h3 className="font-display text-[15px] font-semibold text-ink">
                        {item.title}
                      </h3>
                      <p className="mt-1.5 text-sm leading-relaxed text-muted">{item.desc}</p>
                    </div>
                  </div>
                </Card>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* =================================================================
          CORRIDORS
          ================================================================= */}
      <section id="corridors" className="section border-t border-line bg-surface-sunken/60">
        <div className="container-page">
          <SectionHeading
            eyebrow="Where it works"
            title="Nine destinations, eleven corridors."
            lede="Each with its own checklist, sourced from the published requirements and pinned to a version and a date. Any passport, any origin country."
            align="center"
          />

          <div className="mx-auto mt-10 max-w-2xl">
            <GlobeIllustration className="w-full" />
          </div>

          {error && (
            <div className="mx-auto mt-10 max-w-xl">
              <Alert tone="error" title="Could not load corridors">
                {error}
              </Alert>
            </div>
          )}

          {!corridors && !error && (
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i} className="overflow-hidden">
                  <Skeleton className="h-44 w-full rounded-none" />
                  <div className="space-y-3 p-5">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="h-3 w-full" />
                    <Skeleton className="h-3 w-4/5" />
                  </div>
                </Card>
              ))}
            </div>
          )}

          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {corridors?.map((c, i) => {
              const photo = corridorPhoto(c.key);
              return (
                <Reveal key={c.id} delay={Math.min(i, 5) * 60} className="h-full">
                  <Link href={`/check/new?corridor=${c.id}`} className="group block h-full">
                    <Card variant="interactive" className="flex h-full flex-col overflow-hidden">
                      <Picture
                        photo={photo}
                        ratio="16/10"
                        sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                        imgClassName="transition-transform duration-[900ms] ease-out group-hover:scale-[1.07]"
                      >
                        <div
                          aria-hidden
                          className="absolute inset-0 bg-gradient-to-t from-surface-card via-surface-card/55 to-transparent"
                        />
                        <h3 className="absolute inset-x-4 bottom-3.5 font-display text-lg font-semibold leading-snug text-white [text-shadow:0_2px_12px_rgba(5,9,17,0.9)]">
                          {c.label}
                        </h3>
                      </Picture>

                      <div className="flex flex-1 flex-col p-5">
                        {c.description && (
                          <p className="text-sm leading-relaxed text-muted">{c.description}</p>
                        )}
                        <div className="mt-4 flex flex-wrap items-center gap-2">
                          <Chip className="font-mono text-[11px]">
                            v{c.rulepack_version ?? "—"}
                          </Chip>
                          {c.rulepack_unverified && (
                            <Badge className="border-warn/30 bg-warn/10 text-warn">Draft</Badge>
                          )}
                        </div>
                        <p className="mt-auto pt-5 inline-flex items-center gap-1.5 text-sm font-semibold text-neon-400">
                          See the checklist
                          <span className="transition-transform duration-300 group-hover:translate-x-1">
                            →
                          </span>
                        </p>
                      </div>
                    </Card>
                  </Link>
                </Reveal>
              );
            })}
          </div>

          {corridors?.length === 0 && !error && (
            <div className="mx-auto mt-10 max-w-xl">
              <Alert tone="warning" title="No corridors are enabled yet">
                An administrator needs to publish a rule pack and enable a corridor.
              </Alert>
            </div>
          )}
        </div>
      </section>

      {/* =================================================================
          PRICING
          ================================================================= */}
      <section id="pricing" className="section">
        <div className="container-page">
          <SectionHeading
            eyebrow="Pricing"
            title="Applicants pay once. Agencies subscribe."
            lede="A free check runs every deterministic rule — roughly ninety per cent of what the tool does. Paying adds the AI reading your letters."
            align="center"
          />

          <div className="mx-auto mt-12 grid max-w-6xl items-start gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {PRICING.map((tier, i) => (
              <Reveal key={tier.name} delay={i * 80} className="h-full">
                <Card
                  className={`relative flex h-full flex-col overflow-hidden p-6 ${
                    tier.featured ? "border-neon-500/40 shadow-glow lg:-mt-4 lg:pb-8 lg:pt-8" : ""
                  }`}
                >
                  {tier.featured && (
                    <span className="absolute right-0 top-0 rounded-bl-xl bg-neon-600 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.1em] text-white">
                      Most chosen
                    </span>
                  )}

                  <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">
                    {tier.name}
                  </p>
                  <p className="mt-3 flex items-baseline gap-1">
                    <span className="font-display text-4xl font-bold text-ink-strong">
                      {tier.price}
                    </span>
                    {tier.cadence && (
                      <span className="text-sm font-normal text-muted">{tier.cadence}</span>
                    )}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{tier.lede}</p>

                  <ul className="mt-6 flex-1 space-y-3 border-t border-line pt-6">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-start gap-2.5 text-sm text-ink">
                        <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-good" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <LinkButton
                    href={tier.cta.href}
                    variant={tier.cta.variant}
                    size="lg"
                    className="mt-7 w-full"
                  >
                    {tier.cta.label}
                  </LinkButton>
                </Card>
              </Reveal>
            ))}
          </div>

          <p className="mx-auto mt-8 max-w-xl text-center text-xs leading-relaxed text-muted-soft">
            Credits and tiers are tracked and enforced today; card payment is not yet connected,
            so paid plans are issued manually while that is finished.
          </p>
        </div>
      </section>

      {/* =================================================================
          FAQ
          ================================================================= */}
      <section id="faq" className="section border-t border-line bg-surface-sunken/60">
        <div className="container-page grid gap-12 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
          <SectionHeading
            eyebrow="Questions"
            title="The things people ask first."
            lede="If yours is not here, the report itself explains every rule it applied and where the requirement came from."
          />

          <div className="divide-y divide-line border-y border-line">
            {FAQ.map((item) => (
              <details key={item.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-start justify-between gap-4 text-[15px] font-semibold text-ink transition hover:text-neon-300 [&::-webkit-details-marker]:hidden">
                  {item.q}
                  <ChevronDownIcon className="mt-0.5 h-4 w-4 shrink-0 text-muted transition-transform duration-300 group-open:rotate-180" />
                </summary>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">{item.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* =================================================================
          CLOSING CTA
          ================================================================= */}
      <section className="section-tight">
        <div className="container-page">
          <Card className="relative overflow-hidden border-neon-500/25 px-6 py-12 text-center sm:px-12 sm:py-16">
            <div aria-hidden className="pointer-events-none absolute inset-0 bg-dots opacity-[0.35] mask-radial" />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-x-0 -top-24 h-48 bg-[radial-gradient(ellipse_at_center,rgba(59,130,246,0.22),transparent_70%)]"
            />

            <div className="relative">
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-neon-500/25 bg-neon-500/10 text-neon-400">
                <ShieldIcon className="h-7 w-7" />
              </span>
              <h2 className="mt-6 font-display text-display-sm font-bold text-ink-strong">
                One evening of checking beats one refused application.
              </h2>
              <p className="mx-auto mt-4 max-w-xl leading-relaxed text-muted">
                A refused application costs the fee, the appointment slot, and the weeks before
                the next one. Checking the file first costs nothing.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <LinkButton href="/check/new" variant="primary" size="lg">
                  Run a free check
                  <span aria-hidden>→</span>
                </LinkButton>
                <LinkButton href="/refusals/new" variant="secondary" size="lg">
                  Decode a refusal
                </LinkButton>
              </div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
