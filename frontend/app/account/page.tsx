"use client";

import { useEffect, useState } from "react";

import { Alert, Badge, Card, LinkButton, Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Account } from "@/lib/types";

function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <Card className="p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </Card>
  );
}

export default function AccountPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    api
      .account()
      .then(setAccount)
      .catch((e: Error) => setError(e.message));
  }, [user]);

  if (authLoading || (!account && !error)) return <Loading />;

  return (
    <div className="container-page py-10">
      <h1 className="text-2xl font-bold tracking-tight text-ink">Account</h1>
      <p className="mt-1 text-muted">Your plan, credits and usage.</p>

      {error && (
        <div className="mt-6">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {account && (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Checks remaining"
              value={account.credits}
              hint={account.org_credits > 0 ? `+ ${account.org_credits} in the team pool` : undefined}
            />
            <Stat label="Checks run" value={account.checks_run} />
            {account.user.org ? (
              <>
                <Stat label="Team checks run" value={account.org_checks_run} />
                <Stat label="Team seats" value={account.team_seats} />
              </>
            ) : (
              <Stat
                label="Document retention"
                value={`${account.retention_days} days`}
                hint="Then deleted automatically"
              />
            )}
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <Card className="p-5">
              <h2 className="font-semibold text-ink">Profile</h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Name</dt>
                  <dd className="font-medium text-ink">{account.user.full_name ?? "—"}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Email</dt>
                  <dd className="font-medium text-ink">{account.user.email}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted">Role</dt>
                  <dd>
                    <Badge className="border-line bg-gray-50 text-ink">
                      {account.user.role.replace(/_/g, " ")}
                    </Badge>
                  </dd>
                </div>
                {account.user.org && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-muted">Agency</dt>
                    <dd className="font-medium text-ink">{account.user.org.name}</dd>
                  </div>
                )}
              </dl>
            </Card>

            <Card className="p-5">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-ink">Plan</h2>
                <Badge className="border-brand-600/25 bg-brand-50 text-brand-700">
                  {account.plan}
                </Badge>
              </div>

              <p className="mt-3 text-sm leading-relaxed text-muted">
                Billing is not yet connected in this build. To add credits, ask an
                administrator to grant them from the admin panel.
              </p>

              <div className="mt-4 space-y-2 text-sm">
                <p className="font-medium text-ink">Agency plans</p>
                <ul className="space-y-1 text-muted">
                  <li>Starter — $29/mo, 25 checks</li>
                  <li>Agency — $79/mo, 150 checks, team seats</li>
                  <li>White-label — $199/mo, your logo on reports</li>
                </ul>
              </div>
            </Card>
          </div>

          <Card className="mt-6 bg-gray-50 p-5">
            <h2 className="font-semibold text-ink">Your documents</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Uploaded passports, bank statements and other files are encrypted at rest and
              deleted automatically {account.retention_days} days after a check is created.
              Reports remain available after the source documents are removed. Deleting a
              check removes its files immediately.
            </p>
          </Card>

          <div className="mt-6">
            <LinkButton href="/check/new">Run a new check</LinkButton>
          </div>
        </>
      )}
    </div>
  );
}
