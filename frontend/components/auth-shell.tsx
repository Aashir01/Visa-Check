"use client";

import Link from "next/link";

import { CheckIcon, LockIcon, ShieldIcon } from "./icons";
import { AmbientVideo, MediaScrim } from "./media";
import { CLIP_DEPARTURE_GATE } from "@/lib/media";

/**
 * The frame around signing in and signing up.
 *
 * Both pages were a lone card floating on an empty page, which is the single
 * clearest tell that a product has not shipped yet. The panel beside the form
 * carries the footage and the three commitments about document handling —
 * which is exactly the reassurance someone wants at the moment they are about
 * to hand over scans of their passport.
 */
export function AuthShell({
  title,
  lede,
  children,
  footer,
}: {
  title: string;
  lede: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-2">
      {/* ---------------------------------------------------------------- */}
      {/* Form                                                              */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex items-center justify-center px-5 py-14 sm:px-8 lg:py-20">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h1 className="font-display text-display-sm font-bold text-ink-strong">{title}</h1>
            <p className="mt-2.5 leading-relaxed text-muted">{lede}</p>
          </div>

          {children}

          {footer && <div className="mt-7 text-center text-sm text-muted">{footer}</div>}

          <p className="mt-10 flex items-center justify-center gap-2 text-xs text-muted-soft">
            <LockIcon className="h-3.5 w-3.5" />
            Documents are encrypted at rest and deleted after 30 days.
          </p>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Panel                                                             */}
      {/* ---------------------------------------------------------------- */}
      <aside className="relative isolate hidden overflow-hidden border-l border-line lg:block">
        <AmbientVideo clip={CLIP_DEPARTURE_GATE} />
        <MediaScrim direction="panel" />

        <div className="relative flex h-full flex-col justify-end p-12">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-neon-500/25 bg-neon-500/10 text-neon-400 backdrop-blur">
            <ShieldIcon className="h-6 w-6" />
          </span>

          <blockquote className="mt-7 max-w-md">
            <p className="font-display text-2xl font-semibold leading-snug text-white">
              A refused application costs the fee, the slot, and the weeks before the next one.
            </p>
            <p className="mt-4 leading-relaxed text-slate-300">
              Checking the file first costs nothing. Every deterministic rule — checklist,
              identity, funds, dates, photo spec — runs on a free check.
            </p>
          </blockquote>

          <ul className="mt-9 space-y-3 border-t border-white/10 pt-7">
            {[
              "Encrypted the moment it arrives, never stored as plaintext",
              "Source documents deleted automatically after 30 days",
              "Never used to train models",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-slate-300">
                <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-good" />
                {item}
              </li>
            ))}
          </ul>

          <Link
            href="/"
            className="mt-9 inline-flex w-fit items-center gap-2 text-sm font-medium text-slate-400 transition hover:text-white"
          >
            <span aria-hidden>←</span> Back to the overview
          </Link>
        </div>
      </aside>
    </div>
  );
}
