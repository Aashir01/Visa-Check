"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, Badge, Card, LinkButton, Loading } from "@/components/ui";
import { api } from "@/lib/api";
import type { Corridor } from "@/lib/types";

// --------------------------------------------------------------------------
// Icon components
// --------------------------------------------------------------------------

function ShieldIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M12 2.5 4.5 5.5v6c0 4.6 3.2 8.9 7.5 10 4.3-1.1 7.5-5.4 7.5-10v-6L12 2.5Z" stroke="currentColor" strokeWidth="1.5" />
      <path d="m8.6 12.1 2.3 2.3 4.5-4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function UploadIcon({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M12 16V4m0 0L8 8m4-4 4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckCircle({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="none" className={className} aria-hidden>
      <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.5" />
      <path d="m7 10 2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ScanIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M3 7V5a2 2 0 012-2h2m10 0h2a2 2 0 012 2v2M3 17v2a2 2 0 002 2h2m10 0h2a2 2 0 002-2v-2M7 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ChartIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M18 20V10m-6 10V4M6 20v-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SparkleIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z" fill="currentColor" />
      <path d="M18 15l.8 2.2L21 18l-2.2.8L18 21l-.8-2.2L15 18l2.2-.8L18 15z" fill="currentColor" opacity="0.5" />
    </svg>
  );
}

// --------------------------------------------------------------------------
// Checklist data
// --------------------------------------------------------------------------

const DOCUMENT_CHECKLIST = [
  { label: "Passport", status: "Not Uploaded" },
  { label: "Cover Letter / Purpose of Visit", status: "Not Uploaded" },
  { label: "Bank Statement", status: "Not Uploaded" },
  { label: "Flight Booking", status: "Not Uploaded" },
  { label: "Hotel Booking / Accommodation", status: "Not Uploaded" },
  { label: "Travel Insurance", status: "Not Uploaded" },
  { label: "Additional Documents", status: "Not Uploaded" },
];

const RISK_FACTORS = [
  { factor: "Document Authenticity", risk: "Low Risk", color: "text-neon-500" },
  { factor: "Financial Stability", risk: "Low Risk", color: "text-neon-500" },
  { factor: "Travel History", risk: "Low Risk", color: "text-neon-500" },
  { factor: "Purpose of Visit", risk: "Low Risk", color: "text-neon-500" },
  { factor: "Document Completeness", risk: "Low Risk", color: "text-neon-500" },
  { factor: "Overall Consistency", risk: "Low Risk", color: "text-neon-500" },
];

const HOW_IT_WORKS = [
  { step: "1", title: "UPLOAD", desc: "Upload all required visa documents", icon: UploadIcon },
  { step: "2", title: "ANALYZE", desc: "Our AI system analyzes and verifies", icon: ScanIcon },
  { step: "3", title: "RISK SCORE", desc: "Get risk score and detailed report", icon: ChartIcon },
  { step: "4", title: "IMPROVE", desc: "Follow suggestions to reduce risk", icon: SparkleIcon },
];

// --------------------------------------------------------------------------
// Circular gauge for the risk score (larger, more dramatic)
// --------------------------------------------------------------------------

function RiskGauge({ score }: { score: number }) {
  const size = 200;
  const stroke = 14;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference;
  const color = score >= 85 ? "#00E666" : score >= 65 ? "#EAB308" : score >= 40 ? "#FFB84D" : "#FF4D4D";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Outer glow ring */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle, ${color}15 0%, transparent 70%)`,
          filter: `blur(20px)`,
        }}
      />
      <svg width={size} height={size} className="-rotate-90 relative z-10">
        {/* Track */}
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} stroke="rgba(255,255,255,0.05)" />
        {/* Score arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          stroke={color}
          style={{ filter: `drop-shadow(0 0 12px ${color})`, transition: "stroke-dasharray 1.5s ease-out" }}
        />
      </svg>
      <div className="absolute z-10 flex flex-col items-center">
        <span className="text-5xl font-bold tabular-nums" style={{ color }}>
          {score}%
        </span>
        <span className="mt-1 text-xs font-semibold uppercase tracking-wider" style={{ color }}>
          LOW RISK
        </span>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Page
// --------------------------------------------------------------------------

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
    <div className="bg-surface min-h-screen">
      {/* ================================================================ */}
      {/*  HERO + MAIN DASHBOARD AREA                                      */}
      {/* ================================================================ */}
      <section className="container-page py-8 lg:py-12">
        <div className="grid gap-8 lg:grid-cols-5">
          {/* ---------------------------------------------------------------- */}
          {/*  LEFT COLUMN — Upload + Checklist (3/5)                          */}
          {/* ---------------------------------------------------------------- */}
          <div className="lg:col-span-3 space-y-6">
            {/* Heading */}
            <div className="animate-slide-up">
              <Badge className="border-neon-500/20 bg-neon-500/10 text-neon-400 mb-4">
                <SparkleIcon className="h-3.5 w-3.5" />
                AI POWERED VISA SECURITY CHECK SYSTEM
              </Badge>
              <h1 className="text-3xl font-bold leading-tight tracking-tight text-ink sm:text-4xl lg:text-5xl">
                Upload your documents and get an{" "}
                <span className="text-neon-500">AI risk analysis</span> to avoid visa rejection.
              </h1>
            </div>

            {/* Upload drop zone */}
            <Card className="border-glow overflow-hidden animate-slide-up" style={{ animationDelay: "0.1s" }}>
              <div className="drop-zone m-4 flex flex-col items-center justify-center rounded-xl py-14 px-6 text-center cursor-pointer transition-all duration-300">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-neon-500/10 border border-neon-500/20 mb-4">
                  <UploadIcon className="h-8 w-8 text-neon-500" />
                </div>
                <p className="text-lg font-semibold text-ink">DRAG & DROP FILES HERE</p>
                <p className="mt-1 text-sm text-muted">or click to upload</p>
                <p className="mt-3 text-xs text-muted/60">
                  Supported formats: PDF, JPG, PNG (Max 20MB each)
                </p>
              </div>
            </Card>

            {/* Document checklist */}
            <Card className="border-glow animate-slide-up" style={{ animationDelay: "0.2s" }}>
              <div className="flex items-center gap-2 border-b border-line px-5 py-4">
                <CheckCircle className="h-5 w-5 text-neon-500" />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-ink">DOCUMENT CHECKLIST</h2>
              </div>
              <div className="divide-y divide-line">
                {DOCUMENT_CHECKLIST.map((item) => (
                  <div key={item.label} className="flex items-center justify-between px-5 py-3.5 hover:bg-surface-hover transition-colors">
                    <span className="text-sm text-ink">{item.label}</span>
                    <span className="text-xs font-medium text-muted bg-surface-elevated border border-line rounded-full px-2.5 py-1">
                      {item.status}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* ---------------------------------------------------------------- */}
          {/*  RIGHT COLUMN — Risk Score + Analysis (2/5)                      */}
          {/* ---------------------------------------------------------------- */}
          <div className="lg:col-span-2 space-y-6">
            {/* Risk Score Card */}
            <Card className="border-glow-strong overflow-hidden animate-slide-up" style={{ animationDelay: "0.15s" }}>
              <div className="border-b border-line px-5 py-4">
                <div className="flex items-center gap-2">
                  <ShieldIcon className="h-5 w-5 text-neon-500" />
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-ink">VISA RISK SCORE</h2>
                </div>
                <p className="mt-0.5 text-xs text-muted">AI ANALYSIS</p>
              </div>
              <div className="flex flex-col items-center py-8 px-4">
                <p className="text-xs font-medium text-muted mb-3 uppercase tracking-wider">
                  Based on AI analysis of your documents, your visa rejection risk is
                </p>
                <RiskGauge score={23} />
                <div className="mt-6 w-full rounded-xl bg-neon-500/5 border border-neon-500/10 p-4 text-center">
                  <p className="text-sm font-semibold text-neon-400">GOOD NEWS!</p>
                  <p className="mt-1 text-xs text-muted">
                    Your visa application has a low risk of rejection.
                  </p>
                </div>
              </div>
            </Card>

            {/* Risk Factors Analysis */}
            <Card className="border-glow animate-slide-up" style={{ animationDelay: "0.25s" }}>
              <div className="border-b border-line px-5 py-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-ink">RISK FACTORS ANALYSIS</h2>
              </div>
              <div className="divide-y divide-line">
                <div className="flex items-center justify-between px-5 py-3 text-xs font-semibold uppercase tracking-wider text-muted">
                  <span>Factor</span>
                  <span>Risk</span>
                </div>
                {RISK_FACTORS.map((item) => (
                  <div key={item.factor} className="flex items-center justify-between px-5 py-3 hover:bg-surface-hover transition-colors">
                    <span className="text-sm text-ink">{item.factor}</span>
                    <span className={`text-xs font-semibold ${item.color} flex items-center gap-1.5`}>
                      <span className="h-1.5 w-1.5 rounded-full bg-current" />
                      {item.risk}
                    </span>
                  </div>
                ))}
              </div>
              <div className="border-t border-line px-5 py-4">
                <button className="w-full rounded-lg bg-neon-600 text-black font-semibold text-sm py-2.5 px-4 hover:bg-neon-500 transition-colors shadow-glow-sm">
                  VIEW DETAILED REPORT
                </button>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/*  HOW IT WORKS                                                    */}
      {/* ================================================================ */}
      <section id="how" className="border-t border-line bg-surface-elevated py-16">
        <div className="container-page">
          <div className="text-center mb-12">
            <Badge className="border-neon-500/20 bg-neon-500/10 text-neon-400 mb-4">
              SIMPLE 4-STEP PROCESS
            </Badge>
            <h2 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">HOW IT WORKS</h2>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {HOW_IT_WORKS.map((item, i) => (
              <Card key={item.step} className="border-glow p-6 text-center group hover:border-neon-500/30 transition-all duration-300 animate-slide-up" style={{ animationDelay: `${i * 0.1}s` }}>
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-neon-500/10 border border-neon-500/20 mx-auto mb-4 group-hover:shadow-glow transition-all">
                  <item.icon className="h-7 w-7 text-neon-500" />
                </div>
                <div className="inline-flex items-center justify-center h-7 w-7 rounded-full bg-neon-600 text-black text-xs font-bold mb-3">
                  {item.step}
                </div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-ink mb-1">{item.title}</h3>
                <p className="text-xs text-muted leading-relaxed">{item.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/*  CORRIDORS (keep existing logic)                                  */}
      {/* ================================================================ */}
      <section id="pricing" className="container-page py-16">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-bold tracking-tight text-ink">Pick your corridor</h2>
          <p className="mt-2 text-muted max-w-xl mx-auto">
            We cover three corridors in depth rather than thirty superficially. Accuracy is the whole product.
          </p>
        </div>

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
              <Card className="h-full p-5 border-glow transition-all duration-300 group-hover:border-neon-500/30 group-hover:shadow-glow">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold leading-snug text-ink">{c.label}</h3>
                </div>
                {c.description && (
                  <p className="mt-2 text-sm leading-relaxed text-muted">{c.description}</p>
                )}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Badge className="border-line bg-surface-hover text-muted">
                    checklist v{c.rulepack_version ?? "—"}
                  </Badge>
                  {c.rulepack_unverified && (
                    <Badge className="border-warn/30 bg-warn/10 text-warn">
                      draft
                    </Badge>
                  )}
                </div>
                <p className="mt-4 text-sm font-medium text-neon-500">
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

      {/* ================================================================ */}
      {/*  ABOUT US / PRICING                                              */}
      {/* ================================================================ */}
      <section id="about" className="border-t border-line bg-surface-elevated py-16">
        <div className="container-page">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold tracking-tight text-ink">Pricing</h2>
            <p className="mt-2 text-muted">Applicants pay once. Agencies subscribe.</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-3 max-w-4xl mx-auto">
            {/* Free tier */}
            <Card className="p-6 border-glow">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">Free</p>
              <p className="mt-2 text-3xl font-bold text-ink">$0</p>
              <p className="mt-1 text-sm text-muted">The full checklist for your corridor.</p>
              <ul className="mt-5 space-y-2 text-sm text-ink">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  Complete document checklist
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  Key thresholds for your profile
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  One full analysis to try it
                </li>
              </ul>
              <LinkButton href="/check/new" variant="secondary" className="mt-6 w-full">
                Start free
              </LinkButton>
            </Card>

            {/* Pro tier */}
            <Card className="p-6 border-neon-500/30 shadow-glow relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-neon-600 text-black text-[10px] font-bold uppercase px-3 py-1 rounded-bl-lg tracking-wider">
                Popular
              </div>
              <p className="text-xs font-semibold uppercase tracking-wider text-neon-400">Per Check</p>
              <p className="mt-2 text-3xl font-bold text-ink">
                $19<span className="text-base text-muted font-normal">/check</span>
              </p>
              <p className="mt-1 text-sm text-muted">Full AI-powered analysis with detailed report.</p>
              <ul className="mt-5 space-y-2 text-sm text-ink">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  Everything in Free
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  AI letter review
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  Branded PDF report
                </li>
              </ul>
              <LinkButton href="/check/new" variant="primary" className="mt-6 w-full">
                Run a check
              </LinkButton>
            </Card>

            {/* Agency tier */}
            <Card className="p-6 border-glow">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted">Agency</p>
              <p className="mt-2 text-3xl font-bold text-ink">
                $99<span className="text-base text-muted font-normal">/mo</span>
              </p>
              <p className="mt-1 text-sm text-muted">For consultancies handling multiple applicants.</p>
              <ul className="mt-5 space-y-2 text-sm text-ink">
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  50 checks per month
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  White-label reports
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-neon-500 shrink-0" />
                  Priority support
                </li>
              </ul>
              <LinkButton href="/register" variant="neon" className="mt-6 w-full">
                Get started
              </LinkButton>
            </Card>
          </div>
        </div>
      </section>

      {/* ================================================================ */}
      {/*  DISCLAIMER                                                      */}
      {/* ================================================================ */}
      <section className="container-page py-10">
        <p className="text-xs leading-relaxed text-muted text-center max-w-3xl mx-auto">
          <strong className="text-ink">Important.</strong> VisaGuard is a document completeness checker, not an
          immigration adviser. It reports whether your documents match a named checklist at a stated version and date.
          It does not give legal or eligibility advice, and nothing it produces predicts the outcome of any visa application.
          Consular requirements change without notice and vary between consulates and individual cases.
        </p>
      </section>
    </div>
  );
}
