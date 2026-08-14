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
    <div className="min-h-screen bg-surface">
      <header className="border-b border-line bg-surface-elevated">
        <div className="container-page flex h-16 items-center justify-between gap-4">
          <Link href="/admin" className="flex items-center gap-2">
            <ShieldMark className="h-5 w-5" />
            <span className="font-bold tracking-tight text-ink">VisaGuard</span>
            <span className="rounded bg-ink px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
              admin
            </span>
          </Link>

          <div className="flex items-center gap-3 text-sm">
            <Link href="/checks" className="text-muted transition hover:text-ink">
              Client view
            </Link>
            <span className="hidden text-muted sm:inline">{user.email}</span>
            <button
              onClick={logout}
              className="rounded-lg border border-line px-3 py-1.5 font-medium text-ink transition hover:bg-surface-hover"
            >
              Sign out
            </button>
          </div>
        </div>

        <nav className="container-page flex gap-1 overflow-x-auto pb-px">
          {NAV.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition ${
                  active
                    ? "border-neon-500 text-neon-500"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <main>{children}</main>
    </div>
  );
}
