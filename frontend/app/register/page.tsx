"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, Button, Card, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    organization_name: "",
  });
  const [isAgency, setIsAgency] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function update(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (isAgency && !form.organization_name.trim()) {
      setError("Enter your agency name, or switch to a personal account.");
      return;
    }

    setBusy(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        full_name: form.full_name || undefined,
        organization_name: isAgency ? form.organization_name : undefined,
      });
      router.push("/check/new");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="container-narrow max-w-md py-16">
      <Card className="p-6">
        <h1 className="text-xl font-bold text-ink">Create your account</h1>
        <p className="mt-1 text-sm text-muted">
          You get one free check to try the full pipeline.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {error && <Alert tone="error">{error}</Alert>}

          <Field label="Full name">
            <Input
              value={form.full_name}
              onChange={(e) => update("full_name", e.target.value)}
              autoComplete="name"
              placeholder="Ahmed Khan"
            />
          </Field>

          <Field label="Email">
            <Input
              type="email"
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              required
              autoComplete="email"
              placeholder="you@example.com"
            />
          </Field>

          <Field label="Password" hint="At least 8 characters.">
            <Input
              type="password"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </Field>

          <label className="flex items-start gap-2.5 rounded-lg border border-line p-3">
            <input
              type="checkbox"
              checked={isAgency}
              onChange={(e) => setIsAgency(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-line text-brand-700"
            />
            <span className="text-sm">
              <span className="font-medium text-ink">I run a visa consultancy</span>
              <span className="mt-0.5 block text-muted">
                Creates an agency account so your team shares checks and credits.
              </span>
            </span>
          </label>

          {isAgency && (
            <Field label="Agency name">
              <Input
                value={form.organization_name}
                onChange={(e) => update("organization_name", e.target.value)}
                placeholder="Madina Travels"
              />
            </Field>
          )}

          <Button type="submit" disabled={busy} className="w-full">
            {busy && <Spinner />} Create account
          </Button>
        </form>

        <p className="mt-5 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand-700 hover:underline">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
