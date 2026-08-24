"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChevronDownIcon, CloseIcon, LockIcon, MenuIcon } from "./icons";
import { Button, LinkButton } from "./ui";
import { useAuth } from "@/lib/auth";

// --------------------------------------------------------------------------
// Brand
// --------------------------------------------------------------------------

export function ShieldMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={className} aria-hidden>
      <defs>
        <linearGradient id="shield-grad" x1="4" y1="3" x2="20" y2="22">
          <stop stopColor="#60A5FA" />
          <stop offset="1" stopColor="#1D4ED8" />
        </linearGradient>
      </defs>
      <path
        d="M12 2.5 4.5 5.5v6c0 4.6 3.2 8.9 7.5 10 4.3-1.1 7.5-5.4 7.5-10v-6L12 2.5Z"
        fill="url(#shield-grad)"
      />
      <path
        d="m8.6 12.1 2.3 2.3 4.5-4.5"
        stroke="#FFFFFF"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Wordmark({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="group flex items-center gap-2.5" aria-label="VisaGuard — home">
      <ShieldMark className="h-7 w-7 transition-transform duration-300 group-hover:scale-105" />
      <span className="font-display text-[17px] font-bold tracking-tight text-ink-strong">
        Visa<span className="text-neon-400">Guard</span>
      </span>
      {!compact && (
        <span className="hidden items-center whitespace-nowrap rounded-full border border-line bg-surface-hover px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted 2xl:inline-flex">
          Document check
        </span>
      )}
    </Link>
  );
}

// --------------------------------------------------------------------------
// Header
// --------------------------------------------------------------------------

const NAV_LINKS = [
  { href: "/check/new", label: "Check a file" },
  { href: "/refusals/new", label: "Decode a refusal" },
  { href: "/#how", label: "How it works" },
  { href: "/#corridors", label: "Corridors" },
  { href: "/#pricing", label: "Pricing" },
];

export function SiteHeader() {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  // The header starts transparent over the hero and picks up a background once
  // the page moves, so the video is not permanently cropped by a bar.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // A drawer that survives navigation is a trap on mobile.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // The admin area has its own chrome.
  if (pathname?.startsWith("/admin")) return null;

  const isActive = (href: string) =>
    href.startsWith("/#") ? false : pathname === href || pathname?.startsWith(`${href}/`);

  return (
    <>
      <header
        className={`sticky top-0 z-40 transition-all duration-300 ${
          scrolled
            ? "border-b border-line bg-surface/85 backdrop-blur-xl supports-[backdrop-filter]:bg-surface/75"
            : "border-b border-transparent bg-transparent"
        }`}
      >
        <div className="container-page flex h-16 items-center justify-between gap-4 lg:h-[68px]">
          <Wordmark />

          <nav aria-label="Primary" className="hidden items-center gap-0.5 lg:flex">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={`whitespace-nowrap rounded-lg px-2.5 py-2 text-sm font-medium transition-colors xl:px-3 ${
                  isActive(l.href)
                    ? "bg-neon-500/10 text-neon-300"
                    : "text-muted hover:bg-surface-hover hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {loading ? (
              <div className="h-9 w-28 animate-pulse rounded-xl bg-surface-hover" />
            ) : user ? (
              <UserMenu user={user} onLogout={logout} />
            ) : (
              <div className="hidden items-center gap-2 sm:flex">
                <LinkButton href="/login" variant="ghost" size="sm">
                  Sign in
                </LinkButton>
                <LinkButton href="/check/new" variant="primary" size="sm">
                  Run a free check
                </LinkButton>
              </div>
            )}

            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-label={open ? "Close menu" : "Open menu"}
              aria-expanded={open}
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-line text-ink transition hover:bg-surface-hover lg:hidden"
            >
              {open ? <CloseIcon /> : <MenuIcon />}
            </button>
          </div>
        </div>
      </header>

      <MobileMenu open={open} onClose={() => setOpen(false)} user={user} onLogout={logout} />
    </>
  );
}

// --------------------------------------------------------------------------
// Signed-in menu
// --------------------------------------------------------------------------

type SessionUser = ReturnType<typeof useAuth>["user"];

function UserMenu({ user, onLogout }: { user: NonNullable<SessionUser>; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const initial = (user.full_name || user.email || "?").trim().charAt(0).toUpperCase();

  return (
    <div className="relative" ref={ref}>
      {/* Credits sit outside the menu: it is the number that decides whether
          someone can run the thing they came here to run. */}
      <span className="mr-2 hidden items-center whitespace-nowrap rounded-full border border-line bg-surface-hover px-3 py-1.5 text-xs font-medium text-muted xl:inline-flex">
        <span className="tabular font-semibold text-ink">{user.credits}</span>
        <span>{user.credits === 1 ? "check left" : "checks left"}</span>
      </span>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex items-center gap-2 rounded-xl border border-line bg-surface-elevated py-1.5 pl-1.5 pr-2.5 text-sm text-ink transition hover:bg-surface-hover"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-neon-500 to-neon-700 text-xs font-bold text-white">
          {initial}
        </span>
        <span className="hidden max-w-[9rem] truncate font-medium sm:inline">
          {user.full_name || user.email}
        </span>
        <ChevronDownIcon className={`h-4 w-4 text-muted transition ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-60 overflow-hidden rounded-2xl border border-line bg-surface-card shadow-overlay"
        >
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-semibold text-ink">{user.full_name || "Your account"}</p>
            <p className="truncate text-xs text-muted">{user.email}</p>
            {user.org && <p className="mt-1 truncate text-xs text-neon-400">{user.org.name}</p>}
          </div>
          <div className="p-1.5">
            <MenuLink href="/checks">Your checks</MenuLink>
            <MenuLink href="/refusals">Refusals decoded</MenuLink>
            <MenuLink href="/account">Account &amp; credits</MenuLink>
            {user.role === "admin" && <MenuLink href="/admin">Admin console</MenuLink>}
          </div>
          <div className="border-t border-line p-1.5">
            <button
              role="menuitem"
              onClick={onLogout}
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-muted transition hover:bg-surface-hover hover:text-ink"
            >
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function MenuLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      role="menuitem"
      href={href}
      className="block rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-surface-hover hover:text-ink"
    >
      {children}
    </Link>
  );
}

// --------------------------------------------------------------------------
// Mobile drawer
// --------------------------------------------------------------------------

function MobileMenu({
  open,
  onClose,
  user,
  onLogout,
}: {
  open: boolean;
  onClose: () => void;
  user: SessionUser;
  onLogout: () => void;
}) {
  return (
    <div
      className={`fixed inset-0 z-30 lg:hidden ${open ? "" : "pointer-events-none"}`}
      aria-hidden={!open}
    >
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-surface-sunken/80 backdrop-blur-sm transition-opacity duration-300 ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />
      <nav
        aria-label="Mobile"
        className={`absolute inset-x-0 top-16 mx-3 overflow-hidden rounded-2xl border border-line bg-surface-card shadow-overlay transition-all duration-300 ease-out ${
          open ? "translate-y-0 opacity-100" : "-translate-y-3 opacity-0"
        }`}
      >
        <div className="p-2">
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="block rounded-xl px-4 py-3 text-[15px] font-medium text-ink transition hover:bg-surface-hover"
            >
              {l.label}
            </Link>
          ))}
        </div>

        <div className="border-t border-line p-3">
          {user ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between rounded-xl bg-surface-hover px-4 py-3">
                <span className="truncate text-sm text-muted">{user.email}</span>
                <span className="tabular shrink-0 text-sm font-semibold text-ink">
                  {user.credits} left
                </span>
              </div>
              <LinkButton href="/checks" variant="secondary" className="w-full">
                Your checks
              </LinkButton>
              <LinkButton href="/check/new" variant="primary" className="w-full">
                New check
              </LinkButton>
              <Button variant="ghost" className="w-full" onClick={onLogout}>
                Sign out
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <LinkButton href="/check/new" variant="primary" className="w-full">
                Run a free check
              </LinkButton>
              <LinkButton href="/login" variant="secondary" className="w-full">
                Sign in
              </LinkButton>
            </div>
          )}
        </div>
      </nav>
    </div>
  );
}

// --------------------------------------------------------------------------
// Footer
// --------------------------------------------------------------------------

const FOOTER_COLUMNS: { heading: string; links: { href: string; label: string }[] }[] = [
  {
    heading: "Product",
    links: [
      { href: "/check/new", label: "Check a file" },
      { href: "/refusals/new", label: "Decode a refusal" },
      { href: "/#corridors", label: "Corridors covered" },
      { href: "/#pricing", label: "Pricing" },
    ],
  },
  {
    heading: "How it works",
    links: [
      { href: "/#how", label: "The four steps" },
      { href: "/#checks", label: "What gets checked" },
      { href: "/#faq", label: "Questions" },
    ],
  },
  {
    heading: "Account",
    links: [
      { href: "/login", label: "Sign in" },
      { href: "/register", label: "Create an account" },
      { href: "/checks", label: "Your checks" },
      { href: "/account", label: "Credits" },
    ],
  },
];

export function SiteFooter() {
  const pathname = usePathname();
  if (pathname?.startsWith("/admin")) return null;

  return (
    <footer className="mt-auto border-t border-line bg-surface-sunken">
      <div className="container-page py-14">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,2fr)]">
          <div className="max-w-sm">
            <Wordmark compact />
            <p className="mt-4 text-sm leading-relaxed text-muted">
              VisaGuard checks a visa application bundle against the published checklist for
              your corridor — before it reaches the consulate, while there is still time to
              fix it.
            </p>

            <ul className="mt-6 space-y-2.5 text-sm text-muted">
              {[
                "Encrypted at rest",
                "Deleted automatically after 30 days",
                "Never used to train models",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2.5">
                  <LockIcon className="h-3.5 w-3.5 shrink-0 text-good" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid gap-8 sm:grid-cols-3">
            {FOOTER_COLUMNS.map((col) => (
              <div key={col.heading}>
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink">
                  {col.heading}
                </p>
                <ul className="mt-4 space-y-2.5">
                  {col.links.map((l) => (
                    <li key={l.href + l.label}>
                      <Link
                        href={l.href}
                        className="text-sm text-muted transition hover:text-ink"
                      >
                        {l.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 border-t border-line pt-8">
          <p className="text-xs leading-relaxed text-muted-soft">
            <strong className="text-muted">Important.</strong> VisaGuard is a document
            completeness checker, not an immigration adviser. It reports whether your documents
            match a named checklist at a stated version and date. It does not give legal or
            eligibility advice, and nothing it produces predicts the outcome of any visa
            application. Consular requirements change without notice and vary between consulates
            and individual cases. Always confirm requirements with the relevant consulate or a
            qualified adviser.
          </p>
          <p className="mt-6 text-xs text-muted-soft">
            © {new Date().getFullYear()} VisaGuard. Photography and footage licensed from Pexels.
          </p>
        </div>
      </div>
    </footer>
  );
}
