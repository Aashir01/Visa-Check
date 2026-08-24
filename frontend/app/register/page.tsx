"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { CheckIcon } from "@/components/icons";
import { Alert, Button, Field, Input } from "@/components/ui";
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

  // Surfaced under the field as it is typed, rather than only on submit —
  // being told the rule after failing it is the annoying way round.
  const passwordTooShort = form.password.length > 0 && form.password.length < 8;

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
    <AuthShell
      title="Create your account"
      lede="One free check to run the whole pipeline on a real file. No card required."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-neon-400 hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        {error && <Alert tone="error">{error}</Alert>}

        <Field label="Full name" optional>
          <Input
            value={form.full_name}
            onChange={(e) => update("full_name", e.target.value)}
            autoComplete="name"
            placeholder="As it appears on your passport"
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

        <Field
          label="Password"
          hint={passwordTooShort ? undefined : "At least 8 characters."}
          error={passwordTooShort ? "At least 8 characters." : undefined}
        >
          <Input
            type="password"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="••••••••"
          />
        </Field>

        <label
          className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition ${
            isAgency
              ? "border-neon-500/45 bg-neon-500/[0.07]"
              : "border-line-strong bg-surface-elevated hover:border-line-strong hover:bg-surface-hover"
          }`}
        >
          <span
            className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition ${
              isAgency ? "border-neon-500 bg-neon-600 text-white" : "border-line-strong bg-surface"
            }`}
          >
            {isAgency && <CheckIcon className="h-3 w-3" />}
          </span>
          <input
            type="checkbox"
            checked={isAgency}
            onChange={(e) => setIsAgency(e.target.checked)}
            className="sr-only"
          />
          <span className="text-sm">
            <span className="font-medium text-ink">I run a visa consultancy</span>
            <span className="mt-1 block leading-relaxed text-muted">
              Creates an agency account so your team shares checks and credits.
            </span>
          </span>
        </label>

        {isAgency && (
          <Field label="Agency name">
            <Input
              value={form.organization_name}
              onChange={(e) => update("organization_name", e.target.value)}
              placeholder="Your company name"
            />
          </Field>
        )}

        <Button type="submit" loading={busy} size="lg" className="w-full">
          Create account
        </Button>

        <p className="text-center text-xs leading-relaxed text-muted-soft">
          VisaGuard checks documents against a published checklist. It is not an immigration
          adviser and does not give legal advice.
        </p>
      </form>
    </AuthShell>
  );
}
