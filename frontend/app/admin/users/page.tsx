"use client";

import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Input,
  Loading,
  Select,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AdminUser } from "@/lib/types";

const GRANTS = [10, 25, 50, 150];
// Granting AI adds both a check and the AI entitlement for it.
const AI_GRANTS = [5, 25];

export default function AdminUsersPage() {
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback((q?: string) => {
    api.admin
      .users(q)
      .then(setUsers)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function replace(updated: AdminUser) {
    setUsers((list) => list?.map((u) => (u.id === updated.id ? updated : u)) ?? null);
  }

  async function grant(user: AdminUser, credits: number, aiCredits = 0) {
    setBusyId(user.id);
    setError(null);
    try {
      replace(await api.admin.grantCredits(user.id, credits, aiCredits));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not grant credits.");
    } finally {
      setBusyId(null);
    }
  }

  async function update(user: AdminUser, body: { role?: string; is_active?: boolean }) {
    setBusyId(user.id);
    setError(null);
    try {
      replace(await api.admin.updateUser(user.id, body));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update the user.");
    } finally {
      setBusyId(null);
    }
  }

  if (!users && !error) return <Loading />;

  return (
    <div className="container-page py-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Users</h1>
          <p className="mt-0.5 text-sm text-muted">
            Accounts, plans, usage and manual credit grants.
          </p>
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            load(query || undefined);
          }}
        >
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by email"
            className="w-56"
          />
          <Button variant="secondary" type="submit">
            Search
          </Button>
        </form>
      </div>

      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {users?.length === 0 && <EmptyState title="No users found" />}

      <div className="space-y-3">
        {users?.map((user) => (
          <Card key={user.id} className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-ink">{user.email}</span>
                  <Badge className="border-line bg-gray-50 text-muted">
                    {user.role.replace(/_/g, " ")}
                  </Badge>
                  {!user.is_active && (
                    <Badge className="border-critical/25 bg-red-50 text-critical">
                      disabled
                    </Badge>
                  )}
                  {user.org_name && (
                    <Badge className="border-brand-600/25 bg-brand-50 text-brand-700">
                      {user.org_name}
                    </Badge>
                  )}
                </div>

                <p className="mt-1 text-sm text-muted">
                  {user.full_name ?? "No name"} · {user.check_count} checks ·{" "}
                  <span className="font-medium text-ink">{user.credits} checks</span> ·{" "}
                  <span className="font-medium text-ink">{user.ai_credits} AI</span>
                </p>
                <p className="mt-0.5 text-xs text-muted">
                  joined {formatDateTime(user.created_at)}
                  {user.last_login_at && ` · last seen ${formatDateTime(user.last_login_at)}`}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {GRANTS.map((n) => (
                  <Button
                    key={n}
                    variant="secondary"
                    size="sm"
                    onClick={() => void grant(user, n)}
                    disabled={busyId === user.id}
                    title={`Grant ${n} checks (deterministic)`}
                  >
                    +{n}
                  </Button>
                ))}
                {AI_GRANTS.map((n) => (
                  <Button
                    key={`ai-${n}`}
                    variant="ghost"
                    size="sm"
                    onClick={() => void grant(user, n, n)}
                    disabled={busyId === user.id}
                    title={`Grant ${n} full checks including AI letter review`}
                  >
                    +{n} AI
                  </Button>
                ))}

                <div className="w-36">
                  <Select
                    value={user.role}
                    onChange={(e) => void update(user, { role: e.target.value })}
                    disabled={busyId === user.id}
                    className="text-xs"
                    aria-label={`Role for ${user.email}`}
                  >
                    <option value="user">user</option>
                    <option value="agency_admin">agency admin</option>
                    <option value="admin">admin</option>
                  </Select>
                </div>

                <Button
                  variant={user.is_active ? "danger" : "secondary"}
                  size="sm"
                  onClick={() => void update(user, { is_active: !user.is_active })}
                  disabled={busyId === user.id}
                >
                  {user.is_active ? "Disable" : "Enable"}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
