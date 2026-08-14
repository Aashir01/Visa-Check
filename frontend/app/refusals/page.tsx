"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, Badge, Card, EmptyState, LinkButton, Loading } from "@/components/ui";
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

  if (authLoading || (!rows && !error)) return <Loading />;

  return (
    <div className="container-page py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Refusals decoded</h1>
          <p className="mt-1 text-muted">
            Every refusal letter you have had read, and the plan built from it.
          </p>
        </div>
        <LinkButton href="/refusals/new">Decode a refusal</LinkButton>
      </div>

      {error && (
        <Alert tone="error" title="Could not load your refusals">
          {error}
        </Alert>
      )}

      {rows?.length === 0 && (
        <EmptyState
          title="Nothing decoded yet"
          action={<LinkButton href="/refusals/new">Decode a refusal letter</LinkButton>}
        >
          If you have been refused, upload the standard form — the page with the numbered
          boxes — and we will tell you exactly which grounds were given and what each one
          needs before you reapply.
        </EmptyState>
      )}

      <div className="space-y-3">
        {rows?.map((row) => {
          const verdict = VERDICT_STYLE[row.verdict ?? "undecoded"];
          return (
            <Link key={row.id} href={`/refusals/${row.id}`} className="block">
              <Card className="p-4 transition hover:border-neon-500/40 hover:shadow-glow-sm">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-ink">
                        {row.corridor_label ?? "Refusal"}
                      </p>
                      <Badge className={verdict.chip}>{verdict.label}</Badge>
                      {row.ground_codes.length > 0 && (
                        <Badge className="border-line bg-white/5 text-muted">
                          {row.ground_codes.length}{" "}
                          {row.ground_codes.length === 1 ? "ground" : "grounds"}
                        </Badge>
                      )}
                    </div>
                    <p className="mt-0.5 text-sm text-muted">
                      {formatDateTime(row.created_at)}
                      {row.confidence != null && (
                        <> · {Math.round(row.confidence * 100)}% confidence</>
                      )}
                      {row.recheck_id && <> · re-check started</>}
                    </p>
                  </div>
                  <span className="text-sm font-medium text-neon-500">View plan →</span>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
