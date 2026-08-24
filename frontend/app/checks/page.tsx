"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScanIcon } from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  LinkButton,
  ScoreBar,
  SkeletonRows,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { BAND_STYLE, bandFor, formatDateTime, titleCase } from "@/lib/format";
import type { CheckSummary } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  draft: "border-line bg-surface-hover text-muted",
  queued: "border-neon-500/25 bg-neon-500/10 text-neon-300",
  processing: "border-neon-500/25 bg-neon-500/10 text-neon-300",
  complete: "border-good/25 bg-good/10 text-good",
  failed: "border-critical/25 bg-critical/10 text-critical",
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

  const loading = authLoading || (!checks && !error);

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Home" }, { label: "Your checks" }]}
        title="Your checks"
        lede={
          user?.org
            ? `Shared across ${user.org.name} — everyone on the team sees these.`
            : "Every check you have run, newest first."
        }
        actions={
          <>
            <LinkButton href="/refusals" variant="secondary">
              Refusals
            </LinkButton>
            <LinkButton href="/check/new">New check</LinkButton>
          </>
        }
      />

      <div className="container-page py-8 lg:py-10">
        {error && (
          <Alert tone="error" title="Could not load your checks">
            {error}
          </Alert>
        )}

        {loading && <SkeletonRows rows={4} />}

        {checks?.length === 0 && (
          <EmptyState
            title="No checks yet"
            icon={<ScanIcon className="h-6 w-6" />}
            action={<LinkButton href="/check/new">Run your first check</LinkButton>}
          >
            Upload a document bundle and we will check it against the official checklist for
            your corridor — missing documents, name mismatches, funds, dates and photo spec.
          </EmptyState>
        )}

        <div className="space-y-3">
          {checks?.map((check) => {
            const band = check.risk_band ?? bandFor(check.risk_score);
            const isDone = check.status === "complete";
            const href = isDone ? `/check/${check.id}` : `/check/${check.id}/upload`;

            return (
              <Link key={check.id} href={href} className="group block">
                <Card variant="interactive" className="p-4 sm:p-5">
                  <div className="flex flex-wrap items-center gap-4 sm:gap-5">
                    {/* score */}
                    <div className="w-14 shrink-0 text-center">
                      {isDone && check.risk_score != null ? (
                        <>
                          <span
                            className={`tabular font-display text-2xl font-bold ${BAND_STYLE[band].text}`}
                          >
                            {check.risk_score}
                          </span>
                          <span className="block text-[10px] uppercase tracking-wide text-muted-soft">
                            score
                          </span>
                        </>
                      ) : (
                        <span className="text-xs text-muted-soft">—</span>
                      )}
                    </div>

                    {/* details */}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-display font-semibold text-ink">
                          {check.corridor_label ?? "Check"}
                        </p>
                        <Badge className={STATUS_STYLE[check.status] ?? STATUS_STYLE.draft}>
                          {check.status}
                        </Badge>
                      </div>

                      <p className="mt-1 text-sm text-muted">
                        {titleCase(check.applicant_profile)} · {check.document_count}{" "}
                        {check.document_count === 1 ? "document" : "documents"} ·{" "}
                        {formatDateTime(check.created_at)}
                        {check.rulepack_version && (
                          <> · checklist v{check.rulepack_version}</>
                        )}
                      </p>

                      {isDone && (
                        <>
                          <div className="mt-3 max-w-sm">
                            <ScoreBar score={check.risk_score ?? 0} band={band} />
                          </div>
                          <p className="mt-2 text-xs text-muted">
                            {check.critical_count} critical · {check.warning_count} warning ·{" "}
                            {check.info_count} info
                          </p>
                        </>
                      )}
                    </div>

                    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-neon-400">
                      {isDone ? "View report" : "Continue"}
                      <span
                        aria-hidden
                        className="transition-transform duration-300 group-hover:translate-x-1"
                      >
                        →
                      </span>
                    </span>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
