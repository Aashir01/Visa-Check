"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, Badge, Card, LinkButton, Loading, ScoreGauge } from "@/components/ui";
import { api } from "@/lib/api";
import type { Corridor } from "@/lib/types";

const CHECKS = [
  {
    title: "Missing documents",
    body: "Every item on the corridor's checklist, matched against what you uploaded — including the ones that change with your employment status.",
  },
  {
    title: "Name and detail mismatches",
    body: "Your name, date of birth and passport number are compared across every file. A ticket spelled differently from your passport is a real refusal reason.",
  },
  {
    title: "Financial sufficiency",
    body: "Your balance is read from the statement, converted, and compared against the threshold for your trip length. Sudden large deposits are flagged.",
  },
  {
    title: "Photo compliance",
    body: "Dimensions, head size in frame, background, sharpness and colour, measured against the corridor's photo specification.",
  },
  {
    title: "Validity windows",
    body: "Passport validity beyond your return, insurance covering every day of travel, statements and letters still in date at submission.",
  },
  {
    title: "Letter completeness",
    body: "Invitation, employment and cover letters are read for the specific details consulates expect them to contain.",
  },
];

const SAMPLE_ISSUES = [
  {
    severity: "critical" as const,
    title: "Travel insurance cover is below EUR 30,000",
    detail: "Found EUR 15,000, but this corridor requires at least EUR 30,000.",
  },
  {
    severity: "critical" as const,
    title: "Your name is not written the same way on every document",
    detail: 'Passport shows "AHMED RAZA KHAN", but the bank statement shows "AHMAD R KHANN".',
  },
  {
    severity: "warning" as const,
    title: "Bank statement covers less than 6 months",
    detail: "The statement runs about 1.9 months. This corridor expects at least 6.",
  },
];

const SEVERITY_CHIP = {
  critical: "border-critical/30 bg-red-50 text-critical",
  warning: "border-warn/30 bg-amber-50 text-warn",
};

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
    <>
      {/* ---------------- hero ---------------- */}
      <section className="border-b border-line bg-white">
        <div className="container-page grid gap-12 py-16 lg:grid-cols-2 lg:items-center lg:py-24">
          <div>
            <Badge className="border-brand-600/25 bg-brand-50 text-brand-700">
              For applicants and visa consultancies
            </Badge>
            <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-ink sm:text-5xl">
              Find the problems in your visa file{" "}
              <span className="text-brand-700">before the consulate does.</span>
            </h1>
            <p className="mt-5 text-lg leading-relaxed text-muted">
              Upload your document set. VisaGuard checks it against a versioned checklist
              for your exact country and visa type, then tells you what is missing,
              what contradicts itself, and how to fix each one.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <LinkButton href="/check/new" size="lg">
                Run a free check
              </LinkButton>
              <LinkButton href="#how" variant="secondary" size="lg">
                See what it checks
              </LinkButton>
            </div>

            <p className="mt-4 text-sm text-muted">
              The checklist and risk score are free. No card required.
            </p>
          </div>

          {/* sample report preview */}
          <Card className="overflow-hidden shadow-sm">
            <div className="flex items-center justify-between border-b border-line px-5 py-3">
              <span className="text-sm font-semibold text-ink">Sample report</span>
              <span className="text-xs text-muted">Schengen short-stay · v0.1.0</span>
            </div>

            <div className="flex items-center gap-5 px-5 py-6">
              <ScoreGauge score={41} band="elevated" size={124} />
              <div>
                <p className="font-semibold text-warn">Elevated risk</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">
                  Several issues were found that are frequently cited in refusals for this
                  corridor. Fix the critical items before submitting.
                </p>
                <p className="mt-2 text-xs text-muted">
                  2 critical · 1 warning · 14 checks passed
                </p>
              </div>
            </div>

            <div className="space-y-3 border-t border-line bg-gray-50/60 px-5 py-5">
              {SAMPLE_ISSUES.map((issue) => (
                <div key={issue.title} className="rounded-lg border border-line bg-white p-3">
                  <div className="flex items-start gap-2">
                    <span
                      className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${SEVERITY_CHIP[issue.severity]}`}
                    >
                      {issue.severity}
                    </span>
                    <div>
                      <p className="text-sm font-medium leading-snug text-ink">{issue.title}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-muted">{issue.detail}</p>
                    </div>
                  </div>
                </div>
              ))}
              <p className="pt-1 text-center text-xs text-muted">
                Each issue comes with plain-language fix instructions.
              </p>
            </div>
          </Card>
        </div>
      </section>

      {/* ---------------- corridors ---------------- */}
      <section className="container-page py-16">
        <h2 className="text-2xl font-bold tracking-tight text-ink">Pick your corridor</h2>
        <p className="mt-2 max-w-2xl text-muted">
          We cover three corridors in depth rather than thirty superficially. Accuracy is
          the whole product.
        </p>

        {error && (
          <div className="mt-6">
            <Alert tone="error" title="Could not load corridors">
              {error}
            </Alert>
          </div>
        )}

        {!corridors && !error && <Loading label="Loading corridors…" />}

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {corridors?.map((c) => (
            <Link key={c.id} href={`/check/new?corridor=${c.id}`} className="group">
              <Card className="h-full p-5 transition group-hover:border-brand-600 group-hover:shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold leading-snug text-ink">{c.label}</h3>
                </div>
                {c.description && (
                  <p className="mt-2 text-sm leading-relaxed text-muted">{c.description}</p>
                )}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Badge className="border-line bg-gray-50 text-muted">
                    checklist v{c.rulepack_version ?? "—"}
                  </Badge>
                  {c.rulepack_unverified && (
                    <Badge className="border-amber-400/40 bg-amber-50 text-amber-800">
                      draft
                    </Badge>
                  )}
                </div>
                <p className="mt-4 text-sm font-medium text-brand-700">
                  See the checklist →
                </p>
              </Card>
            </Link>
          ))}
        </div>

        {corridors?.length === 0 && !error && (
          <Alert tone="warning" title="No corridors are enabled yet">
            An administrator needs to publish a rule pack and enable a corridor.
          </Alert>
        )}
      </section>

      {/* ---------------- what it checks ---------------- */}
      <section id="how" className="border-y border-line bg-white py-16">
        <div className="container-page">
          <h2 className="text-2xl font-bold tracking-tight text-ink">What gets checked</h2>
          <p className="mt-2 max-w-2xl text-muted">
            Most of this is deterministic: measured, compared and computed rather than
            guessed. AI is used only where judgement is genuinely needed, such as reading
            whether an invitation letter states who is paying.
          </p>

          <div className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
            {CHECKS.map((item) => (
              <div key={item.title}>
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50">
                  <svg viewBox="0 0 20 20" className="h-4 w-4 fill-brand-700" aria-hidden>
                    <path d="M8.3 13.6 4.7 10l1.3-1.3 2.3 2.3 5.7-5.7L15.3 6.6z" />
                  </svg>
                </div>
                <h3 className="mt-3 font-semibold text-ink">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- pricing ---------------- */}
      <section className="container-page py-16">
        <h2 className="text-2xl font-bold tracking-tight text-ink">Pricing</h2>
        <p className="mt-2 text-muted">Applicants pay once. Agencies subscribe.</p>

        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          <Card className="p-6">
            <p className="text-sm font-semibold uppercase tracking-wide text-muted">Free</p>
            <p className="mt-2 text-3xl font-bold text-ink">$0</p>
            <p className="mt-1 text-sm text-muted">The full checklist for your corridor.</p>
            <ul className="mt-5 space-y-2 text-sm text-ink">
              <li>Complete document checklist</li>
              <li>Key thresholds for your profile</li>
              <li>One full analysis to try it</li>
            </ul>
            <LinkButton href="/check/new" variant="secondary" className="mt-6 w-full">
              Start free
            </LinkButton>
          </Card>

          <Card className="border-brand-600 p-6 ring-1 ring-brand-600">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold uppercase tracking-wide text-brand-700">
                Single check
              </p>
              <Badge className="border-brand-600/25 bg-brand-50 text-brand-700">
                Most popular
              </Badge>
            </div>
            <p className="mt-2 text-3xl font-bold text-ink">
              $12 <span className="text-base font-normal text-muted">one-time</span>
            </p>
            <p className="mt-1 text-sm text-muted">Full analysis of one application bundle.</p>
            <ul className="mt-5 space-y-2 text-sm text-ink">
              <li>Every check, including AI letter review</li>
              <li>Severity-ranked issues with fix instructions</li>
              <li>Downloadable PDF report</li>
            </ul>
            <LinkButton href="/check/new" className="mt-6 w-full">
              Run a check
            </LinkButton>
          </Card>

          <Card className="p-6">
            <p className="text-sm font-semibold uppercase tracking-wide text-muted">
              For agencies
            </p>
            <p className="mt-2 text-3xl font-bold text-ink">
              $29 <span className="text-base font-normal text-muted">/month</span>
            </p>
            <p className="mt-1 text-sm text-muted">25 checks a month, from $29.</p>
            <ul className="mt-5 space-y-2 text-sm text-ink">
              <li>Agency $79/mo — 150 checks, team seats</li>
              <li>White-label $199/mo — your logo on reports</li>
              <li>Branded PDF you can hand to your client</li>
            </ul>
            <LinkButton href="/register" variant="secondary" className="mt-6 w-full">
              Create an agency account
            </LinkButton>
          </Card>
        </div>

        <p className="mt-6 text-sm text-muted">
          Billing is not yet connected. Accounts start with a free check so you can try the
          full pipeline.
        </p>
      </section>

      {/* ---------------- honesty ---------------- */}
      <section className="container-page pb-16">
        <Card className="bg-gray-50 p-6">
          <h2 className="font-semibold text-ink">What VisaGuard will never tell you</h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted">
            That you are approved. No tool can know that. VisaGuard reports whether your
            documents match a specific checklist, at a specific version, on a specific
            date — and says so on every report. A clean result means nothing on the
            checklist is missing or contradictory. It is not a prediction, and it is not a
            substitute for advice from a qualified adviser.
          </p>
        </Card>
      </section>
    </>
  );
}
