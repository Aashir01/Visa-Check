"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { FormIcon } from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { Alert, Badge, Card, EmptyState, LinkButton, SkeletonRows } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { VERDICT_STYLE, formatDateTime } from "@/lib/format";
import type { RefusalSummary } from "@/lib/types";

export default function RefusalsPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [rows, setRows] = useState<RefusalSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .listRefusals()
      .then(setRows)
      .catch((e: Error) => setError(e.message));
  }, [user]);

  const loading = authLoading || (!rows && !error);

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Home" }, { label: "Refusals" }]}
        title="Refusals decoded"
        lede="Every refusal letter you have had read, and the recovery plan built from it."
        actions={
          <>
            <LinkButton href="/checks" variant="secondary">
              Your checks
            </LinkButton>
            <LinkButton href="/refusals/new">Decode a refusal</LinkButton>
          </>
        }
      />

      <div className="container-page py-8 lg:py-10">
        {error && (
          <Alert tone="error" title="Could not load your refusals">
            {error}
          </Alert>
        )}

        {loading && <SkeletonRows rows={3} />}

        {rows?.length === 0 && (
          <EmptyState
            title="Nothing decoded yet"
            icon={<FormIcon className="h-6 w-6" />}
            action={<LinkButton href="/refusals/new">Decode a refusal letter</LinkButton>}
          >
            If you have been refused, upload the standard form — the page with the numbered
            boxes — and we will tell you exactly which grounds were given and what each one
            needs before you reapply. It costs nothing.
          </EmptyState>
        )}

        <div className="space-y-3">
          {rows?.map((row) => {
            const verdict = VERDICT_STYLE[row.verdict ?? "undecoded"];
            return (
              <Link key={row.id} href={`/refusals/${row.id}`} className="group block">
                <Card variant="interactive" className="p-4 sm:p-5">
                  <div className="flex flex-wrap items-center gap-4">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-line bg-surface-elevated text-muted">
                      <FormIcon className="h-5 w-5" />
                    </span>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-display font-semibold text-ink">
                          {row.corridor_label ?? "Refusal"}
                        </p>
                        <Badge className={verdict.chip}>{verdict.label}</Badge>
                        {row.ground_codes.length > 0 && (
                          <Badge className="border-line bg-surface-hover text-muted">
                            {row.ground_codes.length}{" "}
                            {row.ground_codes.length === 1 ? "ground" : "grounds"}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-muted">
                        {formatDateTime(row.created_at)}
                        {row.confidence != null && (
                          <> · {Math.round(row.confidence * 100)}% confidence</>
                        )}
                        {row.recheck_id && <> · re-check started</>}
                      </p>
                    </div>

                    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-neon-400">
                      View plan
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
