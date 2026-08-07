import type { RiskBand, Severity } from "./types";

export const SEVERITY_STYLE: Record<Severity, { chip: string; text: string; label: string; dot: string }> = {
  critical: {
    chip: "border-critical/30 bg-red-50 text-critical",
    text: "text-critical",
    label: "Critical",
    dot: "bg-critical",
  },
  warning: {
    chip: "border-warn/30 bg-amber-50 text-warn",
    text: "text-warn",
    label: "Warning",
    dot: "bg-warn",
  },
  info: {
    chip: "border-brand-600/30 bg-brand-50 text-brand-700",
    text: "text-brand-700",
    label: "Info",
    dot: "bg-brand-600",
  },
};

export const BAND_STYLE: Record<RiskBand, { text: string; bar: string; ring: string }> = {
  low: { text: "text-good", bar: "bg-good", ring: "stroke-good" },
  moderate: { text: "text-yellow-600", bar: "bg-yellow-500", ring: "stroke-yellow-500" },
  elevated: { text: "text-warn", bar: "bg-warn", ring: "stroke-warn" },
  high: { text: "text-critical", bar: "bg-critical", ring: "stroke-critical" },
};

export function bandFor(score: number | null | undefined): RiskBand {
  if (score == null) return "high";
  if (score >= 85) return "low";
  if (score >= 65) return "moderate";
  if (score >= 40) return "elevated";
  return "high";
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function formatUsd(n?: number | null, digits = 4): string {
  if (n == null) return "—";
  return `$${n.toFixed(digits)}`;
}

export function titleCase(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Render an evidence value for display. Extracted amounts arrive as raw
 * numbers, so a balance would otherwise read "552000.0" mid-sentence.
 */
export function formatEvidenceValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString()
      : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }
  return String(value);
}

export function confidenceLabel(c?: number | null): { label: string; tone: string } {
  if (c == null) return { label: "unknown", tone: "text-muted" };
  if (c >= 0.75) return { label: "high", tone: "text-good" };
  if (c >= 0.5) return { label: "medium", tone: "text-warn" };
  return { label: "low", tone: "text-critical" };
}
