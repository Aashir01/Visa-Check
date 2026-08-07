"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { Button, LinkButton } from "./ui";

export function ShieldMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <path
        d="M12 2.5 4.5 5.5v6c0 4.6 3.2 8.9 7.5 10 4.3-1.1 7.5-5.4 7.5-10v-6L12 2.5Z"
        className="fill-brand-700"
      />
      <path
        d="m8.6 12.1 2.3 2.3 4.5-4.5"
        stroke="white"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-2">
      <ShieldMark />
      <span className="text-lg font-bold tracking-tight text-ink">VisaGuard</span>
    </Link>
  );
}

export function SiteHeader() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  // The admin area has its own chrome.
  if (pathname?.startsWith("/admin")) return null;

  const links = user
    ? [
        { href: "/checks", label: "My checks" },
        { href: "/account", label: "Account" },
      ]
    : [];

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/90 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Wordmark />

        <nav className="flex items-center gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                pathname === l.href ? "bg-brand-50 text-brand-700" : "text-muted hover:text-ink"
              }`}
            >
              {l.label}
            </Link>
          ))}

          {loading ? null : user ? (
            <div className="ml-2 flex items-center gap-2">
              {user.role === "admin" && (
                <Link
                  href="/admin"
                  className="rounded-lg px-3 py-1.5 text-sm font-medium text-muted transition hover:text-ink"
                >
                  Admin
                </Link>
              )}
              <span className="hidden text-sm text-muted sm:inline">
                {user.credits} {user.credits === 1 ? "check" : "checks"} left
              </span>
              <Button variant="secondary" size="sm" onClick={logout}>
                Sign out
              </Button>
            </div>
          ) : (
            <div className="ml-2 flex items-center gap-2">
              <LinkButton href="/login" variant="secondary" size="sm">
                Sign in
              </LinkButton>
              <LinkButton href="/check/new" size="sm">
                Run a free check
              </LinkButton>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  const pathname = usePathname();
  if (pathname?.startsWith("/admin")) return null;

  return (
    <footer className="mt-20 border-t border-line bg-white">
      <div className="container-page py-10">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-md">
            <Wordmark />
            <p className="mt-3 text-sm text-muted">
              VisaGuard checks a visa application bundle for missing documents and
              inconsistencies before it is submitted.
            </p>
          </div>
          <div className="text-sm">
            <p className="font-medium text-ink">Your documents</p>
            <ul className="mt-2 space-y-1 text-muted">
              <li>Encrypted at rest</li>
              <li>Deleted automatically after 30 days</li>
              <li>Never used to train models</li>
            </ul>
          </div>
        </div>

        <p className="mt-8 border-t border-line pt-6 text-xs leading-relaxed text-muted">
          <strong className="text-ink">Important.</strong> VisaGuard is a document
          completeness checker, not an immigration adviser. It reports whether your
          documents match a named checklist at a stated version and date. It does not give
          legal or eligibility advice, and nothing it produces predicts the outcome of any
          visa application. Consular requirements change without notice and vary between
          consulates and individual cases. Always confirm requirements with the relevant
          consulate or a qualified adviser.
        </p>
      </div>
    </footer>
  );
}
