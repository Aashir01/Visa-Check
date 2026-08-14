"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Alert, Button, Card, Field, Input, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/checks";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-6">
      <h1 className="text-xl font-bold text-ink">Sign in</h1>
      <p className="mt-1 text-sm text-muted">Access your checks and reports.</p>

      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        {error && <Alert tone="error">{error}</Alert>}

        <Field label="Email">
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="you@example.com"
          />
        </Field>

        <Field label="Password">
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </Field>

        <Button type="submit" disabled={busy} className="w-full">
          {busy && <Spinner />} Sign in
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-muted">
        No account?{" "}
        <Link href="/register" className="font-medium text-neon-500 hover:underline">
          Create one
        </Link>
      </p>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <div className="container-narrow max-w-md py-16">
      <Suspense fallback={<Card className="p-6"><Spinner /></Card>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
