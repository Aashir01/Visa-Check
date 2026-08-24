"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Stepper } from "./ui";

/** The three pages between deciding to check a file and reading the report. */
export const CHECK_STEPS = ["Corridor", "Upload", "Report"];

/**
 * The masthead every signed-in page opens with.
 *
 * Consistency is the whole point: a breadcrumb in the same place, a title at
 * the same size, actions at the same edge. Application screens that each
 * invent their own header are the reason a product feels assembled rather
 * than designed.
 */
export function PageHeader({
  title,
  lede,
  breadcrumbs,
  actions,
  steps,
  currentStep,
  children,
}: {
  title: ReactNode;
  lede?: ReactNode;
  breadcrumbs?: { href?: string; label: string }[];
  actions?: ReactNode;
  /** Pass `CHECK_STEPS` on the pages that form the check flow. */
  steps?: string[];
  currentStep?: number;
  children?: ReactNode;
}) {
  return (
    <div className="border-b border-line bg-surface-sunken/50">
      <div className="container-page py-8 lg:py-10">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav aria-label="Breadcrumb" className="mb-4">
            <ol className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
              {breadcrumbs.map((crumb, i) => (
                <li key={crumb.label} className="flex items-center gap-1.5">
                  {i > 0 && (
                    <span aria-hidden className="text-muted-soft">
                      /
                    </span>
                  )}
                  {crumb.href ? (
                    <Link href={crumb.href} className="transition hover:text-ink">
                      {crumb.label}
                    </Link>
                  ) : (
                    <span className="text-ink">{crumb.label}</span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}

        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
          <div className="min-w-0">
            <h1 className="font-display text-2xl font-bold tracking-tight text-ink-strong sm:text-[28px]">
              {title}
            </h1>
            {lede && <p className="mt-2 max-w-2xl leading-relaxed text-muted">{lede}</p>}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>

        {steps && currentStep != null && (
          <Stepper steps={steps} current={currentStep} className="mt-7" />
        )}

        {children}
      </div>
    </div>
  );
}
