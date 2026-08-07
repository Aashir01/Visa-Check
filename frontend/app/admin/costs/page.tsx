"use client";

import { useEffect, useState } from "react";

import { Alert, Button, Card, EmptyState, Loading, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime, formatUsd } from "@/lib/format";
import type { Costs } from "@/lib/types";

/** What a check must cost to stay profitable at the $12 and $29/mo price points. */
const PRICE_POINTS = [
  { label: "$12 single check", revenue: 12 },
  { label: "Starter $29/mo ÷ 25 checks", revenue: 29 / 25 },
  { label: "Agency $79/mo ÷ 150 checks", revenue: 79 / 150 },
];

export default function AdminCostsPage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Costs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [purging, setPurging] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api.admin
      .costs(days)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [days]);

  async function purge() {
    setPurging(true);
    setNotice(null);
    try {
      const res = await api.admin.purge();
      setNotice(
        `Purged documents for ${res.checks_purged} check(s), removing ${res.files_removed} file(s).`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Purge failed.");
    } finally {
      setPurging(false);
    }
  }

  const perCheck = data?.cost_per_check_usd ?? 0;

  return (
    <div className="container-page py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Costs</h1>
          <p className="mt-0.5 text-sm text-muted">
            Token spend per check per corridor. Watch this before pricing, not after.
          </p>
        </div>
        <div className="w-40">
          <Select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </Select>
        </div>
      </div>

      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}
      {notice && (
        <div className="mb-4">
          <Alert tone="success">{notice}</Alert>
        </div>
      )}

      {!data && !error && <Loading />}

      {data && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="p-5">
              <p className="text-sm text-muted">Total spend</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-ink">
                {formatUsd(data.total_usd)}
              </p>
            </Card>
            <Card className="p-5">
              <p className="text-sm text-muted">Checks completed</p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-ink">
                {data.checks_completed}
              </p>
            </Card>
            <Card className="p-5">
              <p className="text-sm text-muted">Cost per check</p>
              <p
                className={`mt-1 text-2xl font-bold tabular-nums ${
                  perCheck > data.budget_per_check_usd ? "text-critical" : "text-good"
                }`}
              >
                {formatUsd(data.cost_per_check_usd)}
              </p>
              <p className="mt-1 text-xs text-muted">
                budget {formatUsd(data.budget_per_check_usd, 2)}
              </p>
            </Card>
            <Card className="p-5">
              <p className="text-sm text-muted">Token prices</p>
              <p className="mt-1 text-sm text-ink">
                ${data.price_in_per_mtok}/Mtok in
                <br />${data.price_out_per_mtok}/Mtok out
              </p>
            </Card>
          </div>

          {/* margin */}
          <Card className="mt-4 p-5">
            <h2 className="font-semibold text-ink">Margin at each price point</h2>
            <p className="mt-1 text-sm text-muted">
              Gross margin on AI cost alone, at the current average of{" "}
              {formatUsd(perCheck)} per check. Hosting and payment fees are not included.
            </p>
            <div className="mt-4 space-y-3">
              {PRICE_POINTS.map((p) => {
                const margin = p.revenue - perCheck;
                const pct = p.revenue > 0 ? (margin / p.revenue) * 100 : 0;
                return (
                  <div key={p.label} className="flex flex-wrap items-center gap-3">
                    <span className="w-56 shrink-0 text-sm text-ink">{p.label}</span>
                    <div className="h-2 min-w-[120px] flex-1 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className={`h-full rounded-full ${pct > 60 ? "bg-good" : pct > 20 ? "bg-yellow-500" : "bg-critical"}`}
                        style={{ width: `${Math.max(2, Math.min(100, pct))}%` }}
                      />
                    </div>
                    <span
                      className={`w-32 shrink-0 text-right text-sm font-medium tabular-nums ${
                        margin > 0 ? "text-good" : "text-critical"
                      }`}
                    >
                      {formatUsd(margin, 3)} ({pct.toFixed(0)}%)
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* by corridor */}
          <Card className="mt-4 p-5">
            <h2 className="font-semibold text-ink">By corridor</h2>
            {data.by_corridor.length === 0 ? (
              <p className="mt-3 text-sm text-muted">
                No AI spend recorded in this period. Either no checks ran, or they ran
                without an API key configured.
              </p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[600px] text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                      <th className="pb-2 font-medium">Corridor</th>
                      <th className="pb-2 text-right font-medium">Checks</th>
                      <th className="pb-2 text-right font-medium">Spend</th>
                      <th className="pb-2 text-right font-medium">Per check</th>
                      <th className="pb-2 text-right font-medium">Tokens in / out</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {data.by_corridor.map((row) => (
                      <tr key={row.corridor_id}>
                        <td className="py-2 pr-3 text-ink">{row.corridor}</td>
                        <td className="py-2 text-right tabular-nums text-muted">
                          {row.checks}
                        </td>
                        <td className="py-2 text-right tabular-nums text-ink">
                          {formatUsd(row.usd)}
                        </td>
                        <td
                          className={`py-2 text-right tabular-nums ${
                            (row.usd_per_check ?? 0) > data.budget_per_check_usd
                              ? "text-critical"
                              : "text-good"
                          }`}
                        >
                          {formatUsd(row.usd_per_check)}
                        </td>
                        <td className="py-2 text-right tabular-nums text-muted">
                          {row.tokens_in.toLocaleString()} /{" "}
                          {row.tokens_out.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card className="p-5">
              <h2 className="font-semibold text-ink">By call type</h2>
              {data.by_kind.length === 0 ? (
                <p className="mt-3 text-sm text-muted">Nothing recorded.</p>
              ) : (
                <table className="mt-3 w-full text-sm">
                  <tbody className="divide-y divide-line">
                    {data.by_kind.map((row) => (
                      <tr key={row.kind}>
                        <td className="py-2 text-ink">{row.kind}</td>
                        <td className="py-2 text-right tabular-nums text-muted">
                          {row.calls} calls
                        </td>
                        <td className="py-2 text-right tabular-nums text-ink">
                          {formatUsd(row.usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>

            <Card className="p-5">
              <h2 className="font-semibold text-ink">Most expensive checks</h2>
              {data.most_expensive_checks.length === 0 ? (
                <p className="mt-3 text-sm text-muted">Nothing recorded.</p>
              ) : (
                <table className="mt-3 w-full text-sm">
                  <tbody className="divide-y divide-line">
                    {data.most_expensive_checks.map((row) => (
                      <tr key={row.check_id}>
                        <td className="py-2">
                          <a
                            href={`/check/${row.check_id}`}
                            className="font-mono text-xs text-brand-700 hover:underline"
                          >
                            {row.check_id.slice(0, 8)}
                          </a>
                          <span className="ml-2 text-xs text-muted">{row.corridor}</span>
                        </td>
                        <td className="py-2 text-right text-xs text-muted">
                          {formatDateTime(row.created_at)}
                        </td>
                        <td className="py-2 text-right tabular-nums text-ink">
                          {formatUsd(row.usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>

          {/* retention */}
          <Card className="mt-4 p-5">
            <h2 className="font-semibold text-ink">Document retention</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted">
              Uploaded documents are deleted automatically once past the retention window,
              leaving the reports intact. Run this from a daily cron
              (<code className="rounded bg-gray-100 px-1">python cli.py purge</code>); the
              button here is for running it on demand.
            </p>
            <Button variant="secondary" onClick={purge} disabled={purging} className="mt-3">
              {purging && <Spinner />} Purge expired documents now
            </Button>
          </Card>
        </>
      )}

      {data && data.checks_completed === 0 && (
        <div className="mt-4">
          <EmptyState title="No completed checks in this period" />
        </div>
      )}
    </div>
  );
}
