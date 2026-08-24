"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ShieldMark } from "@/components/nav";
import { Loading } from "@/components/ui";
import { useAuth, useRequireAuth } from "@/lib/auth";

const NAV = [
  { href: "/admin", label: "Overview", exact: true },
  { href: "/admin/rules", label: "Rule packs" },
  { href: "/admin/corridors", label: "Corridors" },
  { href: "/admin/reviews", label: "Review queue" },
  { href: "/admin/refusals", label: "Refusal insights" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/costs", label: "Costs" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useRequireAuth(true);
  const { logout } = useAuth();
  const pathname = usePathname();

  if (loading || !user || user.role !== "admin") return <Loading />;

  return (
    <div className="min-h-screen bg-surface-sunken">
      {/* The console is deliberately flatter and cooler than the marketing
          side — it is a tool, and it should not look like it is selling. */}
      <header className="sticky top-0 z-30 border-b border-line bg-surface-elevated/95 backdrop-blur-xl">
        <div className="container-wide flex h-16 items-center justify-between gap-4">
          <Link href="/admin" className="flex items-center gap-2.5">
            <ShieldMark className="h-6 w-6" />
            <span className="font-display font-bold tracking-tight text-ink">VisaGuard</span>
            <span className="rounded-md border border-line-strong bg-surface-hover px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted">
              Admin
            </span>
          </Link>

          <div className="flex items-center gap-3 text-sm">
            <Link
              href="/checks"
              className="rounded-lg px-2.5 py-1.5 text-muted transition hover:bg-surface-hover hover:text-ink"
            >
              Client view
            </Link>
            <span className="hidden max-w-[14rem] truncate text-muted md:inline">
              {user.email}
            </span>
            <button
              onClick={logout}
              className="rounded-xl border border-line-strong px-3 py-1.5 font-medium text-ink transition hover:bg-surface-hover"
            >
              Sign out
            </button>
          </div>
        </div>

        <nav aria-label="Admin sections" className="container-wide">
          <div className="no-scrollbar flex gap-1 overflow-x-auto">
            {NAV.map((item) => {
              const active = item.exact
                ? pathname === item.href
                : pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm font-medium transition ${
                    active
                      ? "border-neon-500 text-neon-300"
                      : "border-transparent text-muted hover:border-line-strong hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </header>

      <main>{children}</main>
    </div>
  );
}
