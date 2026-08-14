import type { RefusalVerdict, RiskBand, Severity, TimelineEntry } from "./types";

export const SEVERITY_STYLE: Record<Severity, { chip: string; text: string; label: string; dot: string }> = {
  critical: {
    chip: "border-critical/30 bg-critical/10 text-critical",
    text: "text-critical",
    label: "Critical",
    dot: "bg-critical",
  },
  warning: {
    chip: "border-warn/30 bg-warn/10 text-warn",
    text: "text-warn",
    label: "Warning",
    dot: "bg-warn",
  },
  info: {
    chip: "border-neon-500/30 bg-neon-500/10 text-neon-400",
    text: "text-neon-400",
    label: "Info",
    dot: "bg-neon-500",
  },
};

export const BAND_STYLE: Record<RiskBand, { text: string; bar: string; ring: string; color: string }> = {
  low: { text: "text-neon-500", bar: "bg-neon-500", ring: "stroke-neon-500", color: "#00E666" },
  moderate: { text: "text-yellow-400", bar: "bg-yellow-500", ring: "stroke-yellow-500", color: "#EAB308" },
  elevated: { text: "text-warn", bar: "bg-warn", ring: "stroke-warn", color: "#FFB84D" },
  high: { text: "text-critical", bar: "bg-critical", ring: "stroke-critical", color: "#FF4D4D" },
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

/**
 * A timeline entry's status is about a date the user has not reached yet, so
 * "expiring" has to look different from both fine and broken — it is the state
 * they can still do something about.
 */
export const TIMELINE_STYLE: Record<
  TimelineEntry["status"],
  { chip: string; dot: string; text: string; label: string }
> = {
  ok: {
    chip: "border-good/30 bg-good/10 text-good",
    dot: "bg-good",
    text: "text-good",
    label: "Valid",
  },
  expiring: {
    chip: "border-warn/30 bg-warn/10 text-warn",
    dot: "bg-warn",
    text: "text-warn",
    label: "Expiring",
  },
  expired: {
    chip: "border-critical/30 bg-critical/10 text-critical",
    dot: "bg-critical",
    text: "text-critical",
    label: "Out of date",
  },
  unknown: {
    chip: "border-line bg-white/5 text-muted",
    dot: "bg-white/30",
    text: "text-muted",
    label: "Unknown",
  },
};

export const VERDICT_STYLE: Record<
  RefusalVerdict,
  { label: string; chip: string; text: string }
> = {
  reapply: {
    label: "Fixable — reapply",
    chip: "border-good/30 bg-good/10 text-good",
    text: "text-good",
  },
  reapply_hard: {
    label: "Reapply, but harder",
    chip: "border-warn/30 bg-warn/10 text-warn",
    text: "text-warn",
  },
  seek_advice: {
    label: "Seek advice",
    chip: "border-critical/30 bg-critical/10 text-critical",
    text: "text-critical",
  },
  undecoded: {
    label: "Not decoded",
    chip: "border-line bg-white/5 text-muted",
    text: "text-muted",
  },
};

/** How the grounds were identified. Users deserve to know when a model guessed. */
export function methodLabel(method?: string | null): string {
  switch (method) {
    case "manual":
      return "You selected these grounds";
    case "deterministic":
      return "Read directly from your letter — the official wording and the ticked boxes";
    case "llm":
      return "Interpreted by AI — check it against your letter";
    default:
      return "Not identified";
  }
}

export function confidenceLabel(c?: number | null): { label: string; tone: string } {
  if (c == null) return { label: "unknown", tone: "text-muted" };
  if (c >= 0.75) return { label: "high", tone: "text-good" };
  if (c >= 0.5) return { label: "medium", tone: "text-warn" };
  return { label: "low", tone: "text-critical" };
}
