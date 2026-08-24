"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { AlertIcon, CheckCircleIcon, ChevronDownIcon, InfoIcon, XCircleIcon } from "./icons";
import { BAND_STYLE, bandFor } from "@/lib/format";
import type { RiskBand } from "@/lib/types";

// --------------------------------------------------------------------------
// Surfaces
// --------------------------------------------------------------------------

export function Card({
  children,
  className = "",
  style,
  /** `plain` for a static panel, `interactive` for anything that links away. */
  variant = "plain",
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  variant?: "plain" | "interactive" | "flush";
}) {
  const variants = {
    plain: "border border-line bg-surface-card shadow-card",
    interactive:
      "border border-line bg-surface-card shadow-card hover-lift hover:border-neon-500/35 hover:shadow-float",
    flush: "border border-line bg-surface-elevated",
  };
  return (
    <div className={`surface-lift rounded-2xl ${variants[variant]} ${className}`} style={style}>
      {children}
    </div>
  );
}

/** Header strip for a card, so every panel divides its title the same way. */
export function CardHeader({
  title,
  subtitle,
  icon,
  action,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div className="flex min-w-0 items-start gap-3">
        {icon && (
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-neon-500/20 bg-neon-500/10 text-neon-400">
            {icon}
          </span>
        )}
        <div className="min-w-0">
          <h2 className="font-display text-base font-semibold text-ink">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm leading-relaxed text-muted">{subtitle}</p>}
        </div>
      </div>
      {action}
    </div>
  );
}

/**
 * The heading block that opens a marketing section: eyebrow, title, lede.
 * Having one component keeps the vertical rhythm identical down the page.
 */
export function SectionHeading({
  eyebrow,
  title,
  lede,
  align = "left",
  className = "",
}: {
  eyebrow?: string;
  title: ReactNode;
  lede?: ReactNode;
  align?: "left" | "center";
  className?: string;
}) {
  const centered = align === "center";
  return (
    <div className={`${centered ? "mx-auto max-w-2xl text-center" : "max-w-2xl"} ${className}`}>
      {eyebrow && (
        <p className="eyebrow">{eyebrow}</p>
      )}
      <h2 className="mt-3 font-display text-display-sm font-bold text-ink-strong">{title}</h2>
      {lede && <p className="mt-4 text-base leading-relaxed text-muted sm:text-[17px]">{lede}</p>}
    </div>
  );
}

// --------------------------------------------------------------------------
// Actions
// --------------------------------------------------------------------------

const BUTTON_VARIANTS = {
  primary:
    "bg-neon-600 text-white shadow-glow-sm hover:bg-neon-500 active:bg-neon-700 disabled:opacity-50",
  secondary:
    "border border-line-strong bg-surface-elevated text-ink hover:border-line-strong hover:bg-surface-hover active:bg-surface-active disabled:opacity-50",
  ghost: "text-muted hover:bg-surface-hover hover:text-ink disabled:opacity-50",
  danger:
    "border border-critical/35 bg-critical/10 text-critical hover:bg-critical/20 disabled:opacity-50",
  neon: "border border-neon-500/45 bg-neon-500/10 text-neon-300 hover:border-neon-500/70 hover:bg-neon-500/20 disabled:opacity-50",
  /** Reads as a solid button on top of photography. */
  onMedia: "bg-white/95 text-[#0B1220] hover:bg-white disabled:opacity-50",
} as const;

const BUTTON_SIZES = {
  sm: "h-9 px-3.5 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-[15px]",
} as const;

const BUTTON_BASE =
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold tracking-tight transition-all duration-200 ease-out disabled:cursor-not-allowed";

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  loading = false,
  ...props
}: {
  children: ReactNode;
  variant?: keyof typeof BUTTON_VARIANTS;
  size?: keyof typeof BUTTON_SIZES;
  /** Shows a spinner and blocks the click, without collapsing the button width. */
  loading?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`${BUTTON_BASE} ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
      aria-busy={loading || undefined}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  children,
  variant = "primary",
  size = "md",
  className = "",
}: {
  href: string;
  children: ReactNode;
  variant?: keyof typeof BUTTON_VARIANTS;
  size?: keyof typeof BUTTON_SIZES;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`${BUTTON_BASE} ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
    >
      {children}
    </Link>
  );
}

export function IconButton({
  children,
  label,
  className = "",
  ...props
}: { children: ReactNode; label: string } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      aria-label={label}
      className={`inline-flex h-10 w-10 items-center justify-center rounded-xl text-muted transition hover:bg-surface-hover hover:text-ink ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

// --------------------------------------------------------------------------
// Forms
// --------------------------------------------------------------------------

export function Field({
  label,
  hint,
  error,
  optional,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-2 flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-ink">{label}</span>
        {optional && <span className="text-xs text-muted-soft">Optional</span>}
      </span>
      {children}
      {hint && !error && <span className="mt-1.5 block text-xs leading-relaxed text-muted">{hint}</span>}
      {error && (
        <span className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-critical">
          <XCircleIcon className="h-3.5 w-3.5 shrink-0" />
          {error}
        </span>
      )}
    </label>
  );
}

const inputBase =
  "w-full rounded-xl border border-line-strong bg-surface-elevated px-3.5 text-sm text-ink outline-none transition placeholder:text-muted-soft hover:border-line-strong focus:border-neon-500 focus:ring-2 focus:ring-neon-500/25 disabled:opacity-60";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputBase} h-11 ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  // The native arrow is drawn by the OS and ignores the dark theme, so it is
  // suppressed and replaced with one that matches the rest of the set.
  const { className, ...rest } = props;
  return (
    <span className="relative block">
      <select
        {...rest}
        className={`${inputBase} h-11 cursor-pointer appearance-none pr-10 ${className ?? ""}`}
      />
      <ChevronDownIcon className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
    </span>
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${inputBase} py-3 ${props.className ?? ""}`} />;
}

// --------------------------------------------------------------------------
// Feedback
// --------------------------------------------------------------------------

const ALERT_TONES = {
  info: { box: "border-neon-500/25 bg-neon-500/[0.07] text-neon-200", icon: InfoIcon, mark: "text-neon-400" },
  warning: { box: "border-warn/25 bg-warn/[0.07] text-amber-100", icon: AlertIcon, mark: "text-warn" },
  error: { box: "border-critical/25 bg-critical/[0.07] text-red-100", icon: XCircleIcon, mark: "text-critical" },
  success: { box: "border-good/25 bg-good/[0.07] text-emerald-100", icon: CheckCircleIcon, mark: "text-good" },
} as const;

export function Alert({
  tone = "info",
  title,
  children,
}: {
  tone?: keyof typeof ALERT_TONES;
  title?: string;
  children: ReactNode;
}) {
  const { box, icon: Icon, mark } = ALERT_TONES[tone];
  return (
    <div className={`flex gap-3 rounded-xl border px-4 py-3.5 text-sm ${box}`}>
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${mark}`} />
      <div className="min-w-0 flex-1">
        {title && <p className="mb-1 font-semibold">{title}</p>}
        <div className="leading-relaxed [&_a]:underline [&_a]:underline-offset-2">{children}</div>
      </div>
    </div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`h-4 w-4 animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3.5" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v3.2A4.8 4.8 0 007.2 12H4z" />
    </svg>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-16 text-sm text-muted" role="status">
      <Spinner /> {label}
    </div>
  );
}

/**
 * Placeholder block sized like the content it stands in for.
 *
 * A shimmering outline of the layout tells someone the page is working and
 * roughly what is coming; a centred spinner tells them neither.
 */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}

export function SkeletonRows({ rows = 3, className = "" }: { rows?: number; className?: string }) {
  return (
    <div className={`space-y-3 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="rounded-2xl border border-line bg-surface-card p-5">
          <div className="flex items-center gap-4">
            <Skeleton className="h-12 w-12 rounded-xl" />
            <div className="flex-1 space-y-2.5">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
  icon,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-line-strong bg-surface-elevated/60 px-6 py-14 text-center">
      {icon && (
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-line bg-surface-card text-muted">
          {icon}
        </div>
      )}
      <p className="font-display text-lg font-semibold text-ink">{title}</p>
      {children && <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">{children}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function Badge({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${className}`}
    >
      {children}
    </span>
  );
}

/** Neutral chip, the default when no semantic colour applies. */
export function Chip({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <Badge className={`border-line bg-surface-hover text-muted ${className}`}>{children}</Badge>
  );
}

/** Shown whenever a report rests on a rule pack that is not yet verified (§9). */
export function DraftPackNotice({ version }: { version?: string | null }) {
  return (
    <Alert tone="warning" title="Draft checklist — not yet verified">
      This corridor is running rule pack <span className="font-mono">{version ?? "unknown"}</span>,
      which was drafted from published requirements but has not been checked against live
      casework. Confirm every requirement with the consulate or your adviser before relying on
      it.
    </Alert>
  );
}

// --------------------------------------------------------------------------
// Progress
// --------------------------------------------------------------------------

/**
 * Where someone is in the check flow.
 *
 * Uploading a document set is a multi-page task with a cost at the end, and
 * people abandon multi-page tasks when they cannot see how much is left.
 */
export function Stepper({
  steps,
  current,
  className = "",
}: {
  steps: string[];
  /** Zero-based index of the step in progress. */
  current: number;
  className?: string;
}) {
  return (
    <ol className={`flex flex-wrap items-center gap-x-2 gap-y-3 ${className}`}>
      {steps.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold transition ${
                done
                  ? "bg-good/15 text-good ring-1 ring-good/30"
                  : active
                    ? "bg-neon-600 text-white shadow-glow-sm"
                    : "bg-surface-hover text-muted-soft ring-1 ring-line"
              }`}
              aria-hidden
            >
              {done ? "✓" : i + 1}
            </span>
            <span
              className={`text-xs font-semibold uppercase tracking-wider ${
                active ? "text-ink" : done ? "text-muted" : "text-muted-soft"
              }`}
              aria-current={active ? "step" : undefined}
            >
              {label}
            </span>
            {i < steps.length - 1 && (
              <span aria-hidden className="mx-1 hidden h-px w-8 bg-line-strong sm:block" />
            )}
          </li>
        );
      })}
    </ol>
  );
}

/** A single figure with its label. Used in trust strips and dashboards. */
export function Stat({
  value,
  label,
  hint,
}: {
  value: ReactNode;
  label: string;
  hint?: string;
}) {
  return (
    <div className="flex items-center gap-3.5">
      <span aria-hidden className="h-10 w-[3px] shrink-0 rounded-full bg-gradient-to-b from-neon-400 to-neon-700" />
      <div>
        <p className="font-display text-xl font-bold leading-none text-ink-strong">{value}</p>
        <p className="mt-1.5 text-xs leading-tight text-muted">{label}</p>
        {hint && <p className="text-[11px] text-muted-soft">{hint}</p>}
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Score display
// --------------------------------------------------------------------------

export function ScoreGauge({
  score,
  band,
  size = 148,
  label,
}: {
  score: number;
  band?: RiskBand | null;
  size?: number;
  label?: string;
}) {
  const effective = band ?? bandFor(score);
  const style = BAND_STYLE[effective];
  const stroke = Math.max(8, Math.round(size * 0.068));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference;

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Score ${score} out of 100 — ${effective} risk`}
    >
      {/* A soft bloom in the band colour, so the state is readable before the
          number is. */}
      <div
        aria-hidden
        className="absolute inset-2 rounded-full"
        style={{ background: `radial-gradient(circle, ${style.color}22 0%, transparent 68%)` }}
      />
      <svg width={size} height={size} className="relative -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          stroke="rgba(148,163,184,0.10)"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          stroke={style.color}
          style={{
            filter: `drop-shadow(0 0 6px ${style.color}66)`,
            transition: "stroke-dasharray 1.2s cubic-bezier(0.22,1,0.36,1)",
          }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`tabular font-display font-bold ${style.text}`} style={{ fontSize: size * 0.26 }}>
          {score}
        </span>
        <span className="mt-0.5 text-[11px] uppercase tracking-wider text-muted">
          {label ?? "out of 100"}
        </span>
      </div>
    </div>
  );
}

export function ScoreBar({ score, band }: { score: number; band?: RiskBand | null }) {
  const style = BAND_STYLE[band ?? bandFor(score)];
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.07]">
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${style.bar}`}
        style={{ width: `${Math.max(2, Math.min(100, score))}%` }}
      />
    </div>
  );
}
