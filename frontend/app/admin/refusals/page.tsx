"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, Badge, Card, EmptyState, Loading, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime, formatUsd } from "@/lib/format";
import type { GroundPerformance, RefusalInsights } from "@/lib/types";

/**
 * How the rule packs are actually performing.
 *
 * Every other number in this admin area measures the system against itself:
 * tests pass, rules fire, costs stay under budget. This page is the only one
 * that measures the rules against reality — a real consular officer refused on
 * a specific ground, and either our check had flagged it or it had not.
 *
 * A low catch rate here is the most valuable signal the product produces, and
 * it is the queue of work for the rule packs.
 */
export default function AdminRefusalsPage() {
  const [days, setDays] = useState(90);
  const [data, setData] = useState<RefusalInsights | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api.admin
      .refusalInsights(days)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [days]);

  if (error) {
    return (
      <div className="container-page py-8">
        <Alert tone="error" title="Could not load refusal insights">
          {error}
        </Alert>
      </div>
    );
  }
  if (!data) return <Loading />;

  return (
    <div className="container-page py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <h1 className="text-xl font-bold text-ink">Refusal insights</h1>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            Every decoded refusal, compared against the check that preceded it. A
            ground the consulate cited that our check passed clean is a hole in the
            rules — and it is worth more than any amount of internal testing.
          </p>
        </div>
        <Select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="w-auto"
        >
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </Select>
      </div>

      {data.total === 0 ? (
        <EmptyState title="No refusals decoded in this period">
          Once applicants start uploading refusal letters, this page becomes the
          scoreboard for the rule packs.
        </EmptyState>
      ) : (
        <>
          <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Refusals decoded" value={String(data.decoded)} />
            <Stat
              label="Gradeable"
              value={String(data.graded)}
              hint="Attached to a prior check"
            />
            <Stat
              label="Decoded without AI"
              value={
                data.deterministic_share == null
                  ? "—"
                  : `${Math.round(data.deterministic_share * 100)}%`
              }
              hint="Matched to official wording"
              tone={
                data.deterministic_share != null && data.deterministic_share < 0.7
                  ? "warn"
                  : "good"
              }
            />
            <Stat label="Decode cost" value={formatUsd(data.llm_cost_usd, 2)} />
            <Stat
              label="Grounds we missed"
              value={String(data.gaps.length)}
              tone={data.gaps.length ? "critical" : "good"}
            />
          </div>

          {data.gaps.length > 0 && (
            <div className="mb-6">
              <Alert tone="error" title="Grounds our rules did not catch">
                {data.gaps.map((g) => (
                  <p key={g.code} className="mt-1">
                    <strong>Ground {g.number}</strong> — missed {g.missed} of{" "}
                    {g.caught + g.missed} time(s).{" "}
                    {g.has_rules
                      ? "Rules exist but did not fire — check the thresholds and the extractor for those fields."
                      : "No rule in any pack speaks to this ground at all — that is a gap in the packs, not a tuning problem."}
                  </p>
                ))}
              </Alert>
            </div>
          )}

          <Card className="mb-6 overflow-hidden">
            <div className="border-b border-line px-5 py-4">
              <h2 className="font-semibold text-ink">Per-ground performance</h2>
              <p className="mt-0.5 text-sm text-muted">
                Worst catch rate first — this is the work queue.
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                    <th className="px-5 py-2.5 font-medium">Ground</th>
                    <th className="px-3 py-2.5 font-medium">Cited</th>
                    <th className="px-3 py-2.5 font-medium">Caught</th>
                    <th className="px-3 py-2.5 font-medium">Missed</th>
                    <th className="px-3 py-2.5 font-medium">Catch rate</th>
                    <th className="px-5 py-2.5 font-medium">Rules</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.grounds.map((g) => (
                    <GroundRow key={g.code} g={g} />
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card className="overflow-hidden">
            <div className="border-b border-line px-5 py-4">
              <h2 className="font-semibold text-ink">Recent refusals</h2>
            </div>
            <ul className="divide-y divide-line">
              {data.recent.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                  <span className="font-mono text-xs text-muted">{r.id.slice(0, 8)}</span>
                  <Badge
                    className={
                      r.status === "decoded"
                        ? "border-good/25 bg-good/10 text-good"
                        : "border-line bg-white/5 text-muted"
                    }
                  >
                    {r.status}
                  </Badge>
                  <span className="text-sm text-ink">
                    grounds {r.ground_codes.length ? r.ground_codes.join(", ") : "—"}
                  </span>
                  {r.missed.length > 0 && (
                    <Badge className="border-critical/25 bg-critical/10 text-critical">
                      missed {r.missed.join(", ")}
                    </Badge>
                  )}
                  <span className="ml-auto text-xs text-muted">
                    {r.method}
                    {r.confidence != null && <> · {Math.round(r.confidence * 100)}%</>}
                    {" · "}
                    {formatDateTime(r.created_at)}
                  </span>
                  {r.check_id && (
                    <Link
                      href={`/check/${r.check_id}`}
                      className="text-xs font-medium text-neon-500 hover:underline"
                    >
                      check →
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}

function GroundRow({ g }: { g: GroundPerformance }) {
  const rate = g.catch_rate;
  const tone =
    rate == null
      ? "text-muted"
      : rate >= 0.9
        ? "text-good"
        : rate >= 0.6
          ? "text-warn"
          : "text-critical";

  return (
    <tr>
      <td className="px-5 py-3">
        <p className="font-medium text-ink">
          <span className="text-muted">{g.number}. </span>
          {g.plain}
        </p>
        <p className="mt-0.5 font-mono text-xs text-muted">{g.code}</p>
      </td>
      <td className="px-3 py-3 tabular-nums text-ink">{g.cited}</td>
      <td className="px-3 py-3 tabular-nums text-good">{g.caught}</td>
      <td className={`px-3 py-3 tabular-nums ${g.missed ? "text-critical" : "text-muted"}`}>
        {g.missed}
      </td>
      <td className={`px-3 py-3 tabular-nums font-semibold ${tone}`}>
        {rate == null ? "—" : `${Math.round(rate * 100)}%`}
      </td>
      <td className="px-5 py-3">
        {g.has_rules ? (
          <span className="font-mono text-xs text-muted">
            {g.rule_ids.slice(0, 3).join(", ")}
            {g.rule_ids.length > 3 && ` +${g.rule_ids.length - 3}`}
          </span>
        ) : g.fixable ? (
          <Badge className="border-critical/25 bg-critical/10 text-critical">
            no rules
          </Badge>
        ) : (
          <span className="text-xs text-muted">not a paperwork ground</span>
        )}
      </td>
    </tr>
  );
}

function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "good" | "warn" | "critical";
}) {
  const tones = {
    default: "text-ink",
    good: "text-good",
    warn: "text-warn",
    critical: "text-critical",
  };
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${tones[tone]}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </Card>
  );
}
