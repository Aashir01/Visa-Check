"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { BAND_STYLE, bandFor } from "@/lib/format";
import type { RiskBand } from "@/lib/types";

// --------------------------------------------------------------------------
// primitives — dark theme
// --------------------------------------------------------------------------

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-line bg-surface-card shadow-card ${className}`}>{children}</div>
  );
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "neon";
  size?: "sm" | "md" | "lg";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const variants = {
    primary: "bg-neon-600 text-black hover:bg-neon-500 shadow-glow-sm disabled:opacity-50",
    secondary: "border border-line bg-surface-elevated text-ink hover:bg-surface-hover disabled:opacity-50",
    ghost: "text-neon-500 hover:bg-neon-500/10 disabled:opacity-50",
    danger: "border border-critical/30 bg-critical/10 text-critical hover:bg-critical/20 disabled:opacity-50",
    neon: "border border-neon-500/50 bg-neon-500/10 text-neon-500 hover:bg-neon-500/20 hover:shadow-glow disabled:opacity-50",
  };
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-5 py-2.5 text-base" };
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
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
  variant?: "primary" | "secondary" | "ghost" | "neon";
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const variants = {
    primary: "bg-neon-600 text-black hover:bg-neon-500 shadow-glow-sm",
    secondary: "border border-line bg-surface-elevated text-ink hover:bg-surface-hover",
    ghost: "text-neon-500 hover:bg-neon-500/10",
    neon: "border border-neon-500/50 bg-neon-500/10 text-neon-500 hover:bg-neon-500/20 hover:shadow-glow",
  };
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-5 py-2.5 text-base" };
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 ${variants[variant]} ${sizes[size]} ${className}`}
    >
      {children}
    </Link>
  );
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink">{label}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-muted">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-critical">{error}</span>}
    </label>
  );
}

const inputBase =
  "w-full rounded-lg border border-line bg-surface-elevated px-3 py-2 text-sm text-ink outline-none transition placeholder:text-muted focus:border-neon-500 focus:ring-2 focus:ring-neon-500/20";

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputBase} ${props.className ?? ""}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputBase} ${props.className ?? ""}`} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${inputBase} ${props.className ?? ""}`} />;
}

// --------------------------------------------------------------------------
// feedback
// --------------------------------------------------------------------------

export function Alert({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "warning" | "error" | "success";
  title?: string;
  children: ReactNode;
}) {
  const tones = {
    info: "border-neon-500/20 bg-neon-500/5 text-neon-400",
    warning: "border-warn/20 bg-warn/5 text-warn",
    error: "border-critical/20 bg-critical/5 text-critical",
    success: "border-good/20 bg-good/5 text-good",
  };
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${tones[tone]}`}>
      {title && <p className="mb-0.5 font-semibold">{title}</p>}
      <div>{children}</div>
    </div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`h-4 w-4 animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-12 text-sm text-muted">
      <Spinner /> {label}
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface-hover px-6 py-12 text-center">
      <p className="font-medium text-ink">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
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
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      {children}
    </span>
  );
}

/** Shown whenever a report rests on a rule pack that is not yet verified (§9). */
export function DraftPackNotice({ version }: { version?: string | null }) {
  return (
    <Alert tone="warning" title="Draft checklist — not yet verified">
      This corridor is running rule pack{" "}
      <span className="font-mono">{version ?? "unknown"}</span>, which was drafted from
      published requirements but has not been checked against live casework. Confirm every
      requirement with the consulate or your adviser before relying on it.
    </Alert>
  );
}

// --------------------------------------------------------------------------
// score display
// --------------------------------------------------------------------------

export function ScoreGauge({
  score,
  band,
  size = 148,
}: {
  score: number;
  band?: RiskBand | null;
  size?: number;
}) {
  const effective = band ?? bandFor(score);
  const style = BAND_STYLE[effective];
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className="stroke-white/5"
        />
        {/* Glow ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          className="opacity-20 blur-sm"
          stroke={style.color}
        />
        {/* Score arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          className="transition-all duration-1000"
          stroke={style.color}
          style={{ filter: `drop-shadow(0 0 8px ${style.color})` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-3xl font-bold tabular-nums ${style.text}`}>{score}</span>
        <span className="text-xs text-muted">out of 100</span>
      </div>
    </div>
  );
}

export function ScoreBar({ score, band }: { score: number; band?: RiskBand | null }) {
  const style = BAND_STYLE[band ?? bandFor(score)];
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
      <div
        className={`h-full rounded-full transition-all ${style.bar}`}
        style={{ width: `${Math.max(2, Math.min(100, score))}%` }}
      />
    </div>
  );
}
