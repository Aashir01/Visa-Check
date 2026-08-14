"use client";

import { Badge, Card } from "@/components/ui";
import { TIMELINE_STYLE, formatDate } from "@/lib/format";
import type { TimelineEntry } from "@/lib/types";

/**
 * What in this file goes stale, and when.
 *
 * A checklist answers "is this document valid?". The question that actually
 * decides the application is "is it valid on the day I hand it in?" — and
 * those two answers diverge whenever an appointment is weeks away. This panel
 * exists to make that divergence visible before it costs someone a slot.
 */
export function TimelinePanel({
  timeline,
  submissionDate,
  source,
}: {
  timeline: TimelineEntry[];
  submissionDate?: string | null;
  source?: "appointment" | "today" | null;
}) {
  if (!timeline.length) return null;

  const expired = timeline.filter((t) => t.status === "expired");
  const expiring = timeline.filter((t) => t.status === "expiring");
  const assumed = source !== "appointment";

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-line px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-ink">Validity on your submission date</h2>
          <Badge className="border-line bg-white/5 text-muted">
            {formatDate(submissionDate)}
          </Badge>
        </div>
        <p className="mt-1 text-sm leading-relaxed text-muted">
          {assumed ? (
            <>
              We dated these against <strong className="text-ink">today</strong>, because you
              have not told us your appointment date. Add it and we will re-date everything
              against the day the consulate will actually see it.
            </>
          ) : (
            <>
              Every date below is measured against your appointment, not today — that is the
              date the consulate applies.
            </>
          )}
        </p>

        {(expired.length > 0 || expiring.length > 0) && (
          <div className="mt-3 flex flex-wrap gap-2">
            {expired.length > 0 && (
              <Badge className={TIMELINE_STYLE.expired.chip}>
                {expired.length} out of date by then
              </Badge>
            )}
            {expiring.length > 0 && (
              <Badge className={TIMELINE_STYLE.expiring.chip}>
                {expiring.length} expiring within 14 days
              </Badge>
            )}
          </div>
        )}
      </div>

      <ul className="divide-y divide-line">
        {timeline.map((entry) => {
          const style = TIMELINE_STYLE[entry.status];
          return (
            <li key={`${entry.document_type}.${entry.field}`} className="px-5 py-3.5">
              <div className="flex items-start gap-3">
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${style.dot}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                    <p className="font-medium text-ink">{entry.what}</p>
                    <p className="text-sm tabular-nums text-muted">
                      {formatDate(entry.valid_until)}
                      {entry.days_remaining != null && (
                        <span className={`ml-2 ${style.text}`}>
                          {entry.days_remaining < 0
                            ? `${Math.abs(entry.days_remaining)} day(s) too late`
                            : `${entry.days_remaining} day(s) spare`}
                        </span>
                      )}
                    </p>
                  </div>
                  <p className="mt-0.5 text-sm leading-relaxed text-muted">{entry.detail}</p>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
