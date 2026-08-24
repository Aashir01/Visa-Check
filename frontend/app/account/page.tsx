"use client";

import { useEffect, useState } from "react";

import { LockIcon } from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { Alert, Badge, Card, CardHeader, LinkButton, Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import type { Account } from "@/lib/types";

function StatCard({
  label,
  value,
  hint,
  emphasis = false,
}: {
  label: string;
  value: string | number;
  hint?: string;
  /** The credit balance decides whether they can run anything, so it leads. */
  emphasis?: boolean;
}) {
  return (
    <Card className={`p-5 ${emphasis ? "border-neon-500/30" : ""}`}>
      <p className="text-sm text-muted">{label}</p>
      <p
        className={`tabular mt-1.5 font-display text-2xl font-bold ${
          emphasis ? "text-neon-300" : "text-ink-strong"
        }`}
      >
        {value}
      </p>
      {hint && <p className="mt-1.5 text-xs leading-relaxed text-muted-soft">{hint}</p>}
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
    <div>
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Home" }, { label: "Account" }]}
        title="Account"
        lede="Your plan, credits and usage."
        actions={<LinkButton href="/check/new">Run a new check</LinkButton>}
      />

      <div className="container-page py-8 lg:py-10">
        {error && <Alert tone="error">{error}</Alert>}

        {account && (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                emphasis
                label="Checks remaining"
                value={account.credits}
                hint={
                  account.org_credits > 0
                    ? `+ ${account.org_credits} in the team pool`
                    : undefined
                }
              />
              <StatCard label="Checks run" value={account.checks_run} />
              <StatCard
                label="Full AI checks left"
                value={
                  account.entitlement.ai_always_included
                    ? "Unlimited"
                    : account.entitlement.ai_credits_remaining
                }
                hint={
                  account.entitlement.ai_always_included
                    ? "included on your plan"
                    : "free checks are deterministic only"
                }
              />
              {account.user.org ? (
                <StatCard label="Team checks run" value={account.org_checks_run} />
              ) : (
                <StatCard
                  label="Checks left today"
                  value={account.checks_left_today}
                  hint={`daily limit ${account.daily_check_limit}`}
                />
              )}
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              {/* ---------------------------------------------------------- */}
              <Card>
                <CardHeader title="Profile" />
                <dl className="divide-y divide-line">
                  {[
                    { term: "Name", value: account.user.full_name ?? "—" },
                    { term: "Email", value: account.user.email },
                  ].map((row) => (
                    <div key={row.term} className="flex justify-between gap-4 px-5 py-3.5 text-sm">
                      <dt className="text-muted">{row.term}</dt>
                      <dd className="truncate font-medium text-ink">{row.value}</dd>
                    </div>
                  ))}
                  <div className="flex items-center justify-between gap-4 px-5 py-3.5 text-sm">
                    <dt className="text-muted">Role</dt>
                    <dd>
                      <Badge className="border-line bg-surface-hover text-ink">
                        {account.user.role.replace(/_/g, " ")}
                      </Badge>
                    </dd>
                  </div>
                  {account.user.org && (
                    <div className="flex justify-between gap-4 px-5 py-3.5 text-sm">
                      <dt className="text-muted">Agency</dt>
                      <dd className="font-medium text-ink">{account.user.org.name}</dd>
                    </div>
                  )}
                  {account.user.org && (
                    <div className="flex justify-between gap-4 px-5 py-3.5 text-sm">
                      <dt className="text-muted">Team seats</dt>
                      <dd className="tabular font-medium text-ink">{account.team_seats}</dd>
                    </div>
                  )}
                </dl>
              </Card>

              {/* ---------------------------------------------------------- */}
              <Card>
                <CardHeader
                  title="Plan"
                  action={
                    <Badge className="border-neon-500/25 bg-neon-500/10 text-neon-300">
                      {account.plan}
                    </Badge>
                  }
                />

                <div className="space-y-4 p-5">
                  <div className="rounded-xl border border-line bg-surface-elevated p-4 text-sm">
                    <p className="font-medium text-ink">What a free check includes</p>
                    <p className="mt-1.5 leading-relaxed text-muted">
                      Every checklist, identity, financial, date and photo rule — missing
                      documents, name and date mismatches across your files, funds against the
                      corridor threshold, passport and insurance validity, and photo compliance.
                      A full check adds an AI review of your invitation, employment and cover
                      letters.
                    </p>
                  </div>

                  <div>
                    <p className="text-sm font-medium text-ink">Paid plans</p>
                    <ul className="mt-2.5 space-y-2 text-sm">
                      {[
                        { name: "Starter", price: "$29/mo", detail: "25 checks" },
                        { name: "Agency", price: "$79/mo", detail: "150 checks, team seats" },
                        {
                          name: "White-label",
                          price: "$199/mo",
                          detail: "your logo on reports",
                        },
                      ].map((plan) => (
                        <li
                          key={plan.name}
                          className="flex items-baseline justify-between gap-3 border-b border-line pb-2 last:border-0"
                        >
                          <span className="text-ink">
                            {plan.name}{" "}
                            <span className="text-muted-soft">— {plan.detail}</span>
                          </span>
                          <span className="shrink-0 font-medium text-muted">{plan.price}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <Alert tone="info">
                    Billing is not connected in this build. To add credits, ask an
                    administrator to grant them from the admin panel.
                  </Alert>
                </div>
              </Card>
            </div>

            {/* ------------------------------------------------------------ */}
            <Card className="mt-6">
              <CardHeader icon={<LockIcon className="h-4 w-4" />} title="Your documents" />
              <p className="p-5 text-sm leading-relaxed text-muted">
                Uploaded passports, bank statements and other files are encrypted at rest and
                deleted automatically {account.retention_days} days after a check is created.
                Reports remain available after the source documents are removed. Deleting a
                check removes its files immediately, with no waiting period. Nothing you upload
                is used to train models.
              </p>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
