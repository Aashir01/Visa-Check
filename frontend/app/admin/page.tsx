"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, Card, Loading, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { formatUsd } from "@/lib/format";
import type { Overview } from "@/lib/types";

function Stat({
  label,
  value,
  hint,
  tone = "default",
  href,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "warn" | "good" | "critical";
  href?: string;
}) {
  const tones = {
    default: "text-ink",
    warn: "text-warn",
    good: "text-good",
    critical: "text-critical",
  };
  const body = (
    <Card className={`p-5 ${href ? "transition hover:border-neon-500/40" : ""}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${tones[tone]}`}>{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </Card>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

export default function AdminOverviewPage() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api
      .admin.overview(days)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [days]);

  const overBudget =
    data?.cost_per_check_usd != null &&
    data.cost_per_check_usd > data.budget_per_check_usd;

  return (
    <div className="container-page py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Overview</h1>
          <p className="mt-0.5 text-sm text-muted">
            Volume, reliability and unit economics.
          </p>
        </div>
        <div className="w-40">
          <Select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </Select>
        </div>
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {!data && !error && <Loading />}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Checks today" value={data.checks_today} />
            <Stat label={`Checks (${days}d)`} value={data.checks_period} />
            <Stat
              label="Completed"
              value={data.completed}
              tone="good"
              hint={
                data.completion_rate != null
                  ? `${(data.completion_rate * 100).toFixed(0)}% completion rate`
                  : undefined
              }
            />
            <Stat
              label="Failed"
              value={data.failed}
              tone={data.failed > 0 ? "critical" : "default"}
            />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="LLM spend"
              value={formatUsd(data.llm_spend_usd)}
              hint={`over ${days} days`}
            />
            <Stat
              label="Cost per check"
              value={formatUsd(data.cost_per_check_usd)}
              tone={overBudget ? "critical" : "good"}
              hint={`budget ${formatUsd(data.budget_per_check_usd, 2)}`}
              href="/admin/costs"
            />
            <Stat
              label="Average risk score"
              value={data.avg_risk_score ?? "—"}
              hint="across completed checks"
            />
            <Stat
              label="Average duration"
              value={data.avg_duration_ms != null ? `${(data.avg_duration_ms / 1000).toFixed(1)}s` : "—"}
            />
          </div>

          {overBudget && (
            <div className="mt-6">
              <Alert tone="error" title="Cost per check is over budget">
                Checks are averaging {formatUsd(data.cost_per_check_usd)} against a budget
                of {formatUsd(data.budget_per_check_usd, 2)}. Review which corridors are
                driving it on the costs page before this eats the margin on a $12 check.
              </Alert>
            </div>
          )}

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Queue depth"
              value={data.queue.queued}
              tone={data.queue.queued > 20 ? "warn" : "default"}
              hint={`${data.queue.processing} running · ${data.queue.worker_mode} mode`}
            />
            <Stat
              label="Oldest pending"
              value={
                data.queue.oldest_pending_seconds != null
                  ? `${Math.round(data.queue.oldest_pending_seconds / 60)}m`
                  : "—"
              }
              tone={
                (data.queue.oldest_pending_seconds ?? 0) > 600 ? "critical" : "default"
              }
              hint="time in queue"
            />
            <Stat
              label="Free tier AI"
              value={data.free_tier_ai_enabled ? "on" : "off"}
              tone={data.free_tier_ai_enabled ? "warn" : "good"}
              hint={
                data.free_tier_ai_enabled
                  ? "free checks cost tokens"
                  : "free checks cost $0"
              }
            />
            <Stat
              label="Open reviews"
              value={data.open_reviews}
              tone={data.open_reviews > 0 ? "warn" : "default"}
              hint="low-confidence checks awaiting correction"
              href="/admin/reviews"
            />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Users" value={data.users} href="/admin/users" />
            <Stat label="Organisations" value={data.organizations} />
            <Stat
              label="Corridors enabled"
              value={data.corridors_enabled}
              href="/admin/corridors"
            />
          </div>
        </>
      )}
    </div>
  );
}
