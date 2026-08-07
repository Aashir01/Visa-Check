"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Card,
  EmptyState,
  LinkButton,
  Loading,
  ScoreBar,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { BAND_STYLE, bandFor, formatDateTime, titleCase } from "@/lib/format";
import type { CheckSummary } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  draft: "border-line bg-gray-50 text-muted",
  queued: "border-brand-600/25 bg-brand-50 text-brand-700",
  processing: "border-brand-600/25 bg-brand-50 text-brand-700",
  complete: "border-good/25 bg-emerald-50 text-good",
  failed: "border-critical/25 bg-red-50 text-critical",
};

export default function ChecksPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [checks, setChecks] = useState<CheckSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .listChecks()
      .then(setChecks)
      .catch((e: Error) => setError(e.message));
  }, [user]);

  if (authLoading || (!checks && !error)) return <Loading />;

  return (
    <div className="container-page py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Your checks</h1>
          <p className="mt-1 text-muted">
            {user?.org ? `Shared across ${user.org.name}.` : "Every check you have run."}
          </p>
        </div>
        <LinkButton href="/check/new">New check</LinkButton>
      </div>

      {error && (
        <Alert tone="error" title="Could not load your checks">
          {error}
        </Alert>
      )}

      {checks?.length === 0 && (
        <EmptyState
          title="No checks yet"
          action={<LinkButton href="/check/new">Run your first check</LinkButton>}
        >
          Upload a document bundle and we will check it against the official checklist for
          your corridor.
        </EmptyState>
      )}

      <div className="space-y-3">
        {checks?.map((check) => {
          const band = check.risk_band ?? bandFor(check.risk_score);
          const isDone = check.status === "complete";
          const href = isDone ? `/check/${check.id}` : `/check/${check.id}/upload`;

          return (
            <Link key={check.id} href={href} className="block">
              <Card className="p-4 transition hover:border-brand-600 hover:shadow-sm">
                <div className="flex flex-wrap items-center gap-4">
                  {/* score */}
                  <div className="w-16 shrink-0 text-center">
                    {isDone && check.risk_score != null ? (
                      <>
                        <span
                          className={`text-2xl font-bold tabular-nums ${BAND_STYLE[band].text}`}
                        >
                          {check.risk_score}
                        </span>
                        <span className="block text-[10px] uppercase tracking-wide text-muted">
                          score
                        </span>
                      </>
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </div>

                  {/* details */}
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-ink">
                        {check.corridor_label ?? "Check"}
                      </p>
                      <Badge className={STATUS_STYLE[check.status] ?? STATUS_STYLE.draft}>
                        {check.status}
                      </Badge>
                    </div>

                    <p className="mt-0.5 text-sm text-muted">
                      {titleCase(check.applicant_profile)} · {check.document_count}{" "}
                      {check.document_count === 1 ? "document" : "documents"} ·{" "}
                      {formatDateTime(check.created_at)}
                      {check.rulepack_version && <> · checklist v{check.rulepack_version}</>}
                    </p>

                    {isDone && (
                      <>
                        <div className="mt-2 max-w-sm">
                          <ScoreBar score={check.risk_score ?? 0} band={band} />
                        </div>
                        <p className="mt-1.5 text-xs text-muted">
                          {check.critical_count} critical · {check.warning_count} warning ·{" "}
                          {check.info_count} info
                        </p>
                      </>
                    )}
                  </div>

                  <span className="text-sm font-medium text-brand-700">
                    {isDone ? "View report →" : "Continue →"}
                  </span>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
