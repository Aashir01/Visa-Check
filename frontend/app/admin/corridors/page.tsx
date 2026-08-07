"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Alert, Badge, Button, Card, Loading } from "@/components/ui";
import { api } from "@/lib/api";
import type { Corridor } from "@/lib/types";

export default function AdminCorridorsPage() {
  const [corridors, setCorridors] = useState<Corridor[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    api.admin
      .corridors()
      .then(setCorridors)
      .catch((e: Error) => setError(e.message));
  }, []);

  async function toggle(corridor: Corridor) {
    setBusyId(corridor.id);
    setError(null);
    try {
      const updated = await api.admin.updateCorridor(corridor.id, {
        enabled: !corridor.enabled,
      });
      setCorridors((list) =>
        list?.map((c) => (c.id === updated.id ? updated : c)) ?? null,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update the corridor.");
    } finally {
      setBusyId(null);
    }
  }

  if (!corridors && !error) return <Loading />;

  return (
    <div className="container-page py-8">
      <div className="mb-6">
        <h1 className="text-xl font-bold tracking-tight text-ink">Corridors</h1>
        <p className="mt-0.5 text-sm text-muted">
          Which country and visa-type combinations applicants can select. A corridor cannot
          be enabled until it has a published rule pack.
        </p>
      </div>

      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      <div className="space-y-3">
        {corridors?.map((c) => (
          <Card key={c.id} className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold text-ink">{c.label}</h2>
                  <Badge
                    className={
                      c.enabled
                        ? "border-good/25 bg-emerald-50 text-good"
                        : "border-line bg-gray-50 text-muted"
                    }
                  >
                    {c.enabled ? "enabled" : "disabled"}
                  </Badge>
                  {c.rulepack_unverified && (
                    <Badge className="border-amber-400/40 bg-amber-50 text-amber-800">
                      unverified
                    </Badge>
                  )}
                </div>

                {c.description && (
                  <p className="mt-1 text-sm text-muted">{c.description}</p>
                )}

                <p className="mt-2 text-xs text-muted">
                  <code className="rounded bg-gray-100 px-1.5 py-0.5">{c.key}</code>
                  {" · "}
                  {c.origin_country} → {c.destination}
                  {" · "}
                  {c.rulepack_version
                    ? `checklist v${c.rulepack_version}`
                    : "no published checklist"}
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <Link
                  href="/admin/rules"
                  className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink transition hover:bg-gray-50"
                >
                  Edit rules
                </Link>
                <Button
                  variant={c.enabled ? "danger" : "primary"}
                  size="sm"
                  onClick={() => void toggle(c)}
                  disabled={busyId === c.id || (!c.enabled && !c.rulepack_version)}
                  title={
                    !c.enabled && !c.rulepack_version
                      ? "Publish a rule pack before enabling this corridor"
                      : undefined
                  }
                >
                  {c.enabled ? "Disable" : "Enable"}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
