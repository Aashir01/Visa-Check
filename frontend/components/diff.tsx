"use client";

import Link from "next/link";

import { Badge, Card } from "@/components/ui";
import { SEVERITY_STYLE } from "@/lib/format";
import type { CheckDiff, DiffRow } from "@/lib/types";

/**
 * "You still have four issues" is a demoralising and useless thing to be told
 * after an evening of fixing documents. What a person needs after a second
 * attempt is the delta — fixed, still open, new — and, if they are recovering
 * from a refusal, the narrower question of whether the grounds they were
 * actually refused on are now clear.
 */
export function DiffPanel({ diff }: { diff: CheckDiff }) {
  const previous = diff.vs_previous;
  const refusal = diff.vs_refusal;
  if (!previous && !refusal) return null;

  return (
    <div className="space-y-4">
      {refusal && (
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <h2 className="font-semibold text-ink">Against your refusal</h2>
            <p className="mt-1 text-sm leading-relaxed text-muted">{refusal.headline}</p>
          </div>
          <ul className="divide-y divide-line">
            {refusal.grounds.map((g) => (
              <li key={g.code} className="flex items-start gap-3 px-5 py-3">
                <span
                  className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    !g.fixable
                      ? "border-critical/30 bg-critical/10 text-critical"
                      : g.cleared
                        ? "border-good/30 bg-good/10 text-good"
                        : "border-warn/30 bg-warn/10 text-warn"
                  }`}
                >
                  {!g.fixable ? "Not paperwork" : g.cleared ? "Cleared" : "Still open"}
                </span>
                <div className="min-w-0">
                  <p className="text-sm text-ink">
                    <span className="text-muted">Ground {g.number} — </span>
                    {g.plain}
                  </p>
                  {g.still_open_rules.length > 0 && (
                    <p className="mt-1 font-mono text-xs text-muted">
                      {g.still_open_rules.join(", ")}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {refusal.counts.blocking > 0 && (
            <p className="border-t border-line bg-critical/5 px-5 py-3 text-xs leading-relaxed text-muted">
              A ground marked <strong className="text-ink">not paperwork</strong> cannot be
              answered by a better file, so this re-check does not speak to it either way.
            </p>
          )}
        </Card>
      )}

      {previous && (
        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold text-ink">What changed since last time</h2>
              {previous.score_delta != null && (
                <Badge
                  className={
                    previous.score_delta > 0
                      ? "border-good/30 bg-good/10 text-good"
                      : previous.score_delta < 0
                        ? "border-critical/30 bg-critical/10 text-critical"
                        : "border-line bg-white/5 text-muted"
                  }
                >
                  {previous.previous_score} → {previous.score}
                  <span className="tabular-nums">
                    {previous.score_delta > 0 ? ` +${previous.score_delta}` : ` ${previous.score_delta}`}
                  </span>
                </Badge>
              )}
            </div>
            <p className="mt-1 text-sm leading-relaxed text-muted">{previous.headline}</p>
            {previous.previous_check_id && (
              <Link
                href={`/check/${previous.previous_check_id}`}
                className="mt-2 inline-block text-xs font-medium text-neon-500 hover:underline"
              >
                View the earlier report →
              </Link>
            )}
          </div>

          <div className="grid divide-y divide-line sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <DiffColumn
              title="Fixed"
              tone="text-good"
              empty="Nothing from the last report has cleared yet."
              rows={previous.resolved}
              strike
            />
            <DiffColumn
              title="Still open"
              tone="text-warn"
              empty="Nothing carried over — every earlier issue is gone."
              rows={previous.remaining}
            />
            <DiffColumn
              title="New"
              tone="text-critical"
              empty="No new issues appeared."
              rows={previous.introduced}
            />
          </div>
        </Card>
      )}
    </div>
  );
}

function DiffColumn({
  title,
  tone,
  rows,
  empty,
  strike = false,
}: {
  title: string;
  tone: string;
  rows: DiffRow[];
  empty: string;
  strike?: boolean;
}) {
  return (
    <div className="px-5 py-4">
      <h3 className={`text-sm font-semibold ${tone}`}>
        {title} ({rows.length})
      </h3>
      {rows.length === 0 ? (
        <p className="mt-2 text-xs leading-relaxed text-muted">{empty}</p>
      ) : (
        <ul className="mt-2.5 space-y-2">
          {rows.map((row) => (
            <li key={row.rule_id} className="flex items-start gap-2 text-sm">
              <span
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                  SEVERITY_STYLE[row.severity]?.dot ?? "bg-white/30"
                }`}
              />
              <span className={strike ? "text-muted line-through" : "text-ink"}>
                {row.title ?? row.rule_id}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
