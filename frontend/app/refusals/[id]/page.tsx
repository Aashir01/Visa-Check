"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Loading,
  LinkButton,
  Spinner,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { VERDICT_STYLE, formatDateTime, methodLabel } from "@/lib/format";
import type { PlanStep, Refusal } from "@/lib/types";

export default function RefusalPlanPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const router = useRouter();

  const [refusal, setRefusal] = useState<Refusal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    if (!user) return;
    api
      .getRefusal(params.id)
      .then(setRefusal)
      .catch((e: Error) => setError(e.message));
  }, [user, params.id]);

  /**
   * A re-check only makes sense against the check that preceded the refusal —
   * it inherits the corridor, the profile and the travel dates, and carries the
   * refusal forward so the report can answer ground by ground.
   */
  async function startRecheck() {
    if (!refusal?.check_id) return;
    setStarting(true);
    try {
      const child = await api.recheck(refusal.check_id, { refusal_id: refusal.id });
      router.push(`/check/${child.id}/upload`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the re-check.");
      setStarting(false);
    }
  }

  if (authLoading || (!refusal && !error)) return <Loading />;

  if (error) {
    return (
      <div className="container-narrow py-10">
        <Alert tone="error" title="Could not load this refusal">
          {error}
        </Alert>
      </div>
    );
  }
  if (!refusal) return null;

  const plan = refusal.plan;
  const verdict = VERDICT_STYLE[plan?.verdict ?? "undecoded"];
  const steps = plan?.steps ?? [];
  const blocking = steps.filter((s) => !s.fixable);
  const fixable = steps.filter((s) => s.fixable);
  const lowConfidence = (refusal.confidence ?? 0) < 0.7;

  if (!steps.length) {
    return (
      <div className="container-narrow py-10">
        <EmptyState
          title="We could not identify the grounds"
          action={<LinkButton href="/refusals/new">Try again</LinkButton>}
        >
          {plan?.summary ??
            "Upload the page of the form with the numbered, ticked boxes — or select the grounds yourself — and we will build the plan."}
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="container-page py-10">
      {/* header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Recovery plan</h1>
          <p className="mt-1 text-muted">
            {refusal.corridor_label ?? "Refusal"}
            {refusal.consulate && <> · {refusal.consulate}</>}
            {refusal.decision_date && <> · decided {refusal.decision_date}</>}
          </p>
          <p className="mt-1 text-sm text-muted">
            Decoded {formatDateTime(refusal.created_at)} · {methodLabel(refusal.method)}
            {refusal.confidence != null && (
              <> · {Math.round(refusal.confidence * 100)}% confidence</>
            )}
          </p>
        </div>
        <LinkButton href="/refusals" variant="secondary">
          All refusals
        </LinkButton>
      </div>

      {lowConfidence && (
        <div className="mb-6">
          <Alert tone="warning" title="Check this against your own letter">
            We are not fully confident in this reading — the text may not have come through
            cleanly. Compare the grounds below against the ticked boxes on your form, and if
            they do not match,{" "}
            <Link href="/refusals/new" className="font-medium underline">
              select the grounds yourself
            </Link>
            .
          </Alert>
        </div>
      )}

      {/* verdict */}
      <Card className="mb-6 p-6">
        <div className="flex flex-wrap items-center gap-3">
          <Badge className={verdict.chip}>{verdict.label}</Badge>
          {refusal.ground_codes.length > 0 && (
            <Badge className="border-line bg-white/5 text-muted">
              {refusal.ground_codes.length}{" "}
              {refusal.ground_codes.length === 1 ? "ground given" : "grounds given"}
            </Badge>
          )}
        </div>
        <h2 className={`mt-3 text-lg font-semibold ${verdict.text}`}>{plan?.headline}</h2>
        <p className="mt-1.5 max-w-3xl leading-relaxed text-muted">{plan?.summary}</p>

        <div className="mt-5 flex flex-wrap gap-3">
          {plan?.can_recheck && refusal.check_id ? (
            <div>
              <Button onClick={startRecheck} disabled={starting} size="lg">
                {starting && <Spinner />} Rebuild the file and re-check
              </Button>
              <p className="mt-2 text-xs text-muted">
                Free — confirming a fix we asked for does not cost another check.
              </p>
            </div>
          ) : plan?.can_recheck ? (
            <LinkButton
              href={`/check/new?refusal=${refusal.id}${
                refusal.corridor_id ? `&corridor=${refusal.corridor_id}` : ""
              }`}
              size="lg"
            >
              Run a check on the rebuilt file
            </LinkButton>
          ) : null}
          {!plan?.can_recheck && (
            <p className="text-sm text-muted">
              We are not offering a re-check here, because a better file would not answer
              what you were refused on.
            </p>
          )}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-8">
          {blocking.length > 0 && (
            <section>
              <h2 className="font-semibold text-critical">
                Cannot be fixed by reapplying
              </h2>
              <p className="mt-0.5 text-sm text-muted">
                These are not paperwork problems. Reapplying without addressing them risks
                another fee and another refusal on the same ground.
              </p>
              <div className="mt-4 space-y-3">
                {blocking.map((step, i) => (
                  <StepCard key={step.ground_code} step={step} index={i + 1} />
                ))}
              </div>
            </section>
          )}

          {fixable.length > 0 && (
            <section>
              <h2 className="font-semibold text-ink">
                Work through these in order
              </h2>
              <p className="mt-0.5 text-sm text-muted">
                Ordered by what blocks you soonest and costs least to put right.
              </p>
              <div className="mt-4 space-y-3">
                {fixable.map((step, i) => (
                  <StepCard
                    key={step.ground_code}
                    step={step}
                    index={blocking.length + i + 1}
                  />
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className="space-y-4">
          {refusal.appeal?.applicable && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink">Appealing</h2>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                {refusal.appeal.general}
              </p>
              {refusal.appeal.grounds?.map((g) => (
                <p key={g.code} className="mt-2 text-xs leading-relaxed text-warn">
                  <span className="font-medium">Ground {g.number}:</span> {g.note}
                </p>
              ))}
              {refusal.appeal.caution && (
                <p className="mt-3 border-t border-line pt-3 text-xs leading-relaxed text-muted">
                  {refusal.appeal.caution}
                </p>
              )}
            </Card>
          )}

          {(refusal.caught_by_check?.length || refusal.missed_by_check?.length) && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink">
                What our check had told you
              </h2>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                Measured against the check you ran before submitting. We publish this
                because a ground we missed is a gap in our rules, not a footnote.
              </p>
              {refusal.caught_by_check?.map((c) => (
                <p key={c.code} className="mt-2 text-xs text-good">
                  ✓ Ground {c.number} — flagged before you submitted
                </p>
              ))}
              {refusal.missed_by_check?.map((m) => (
                <p key={m.code} className="mt-2 text-xs text-critical">
                  ✗ Ground {m.number} — our check did not flag this
                </p>
              ))}
              {refusal.check_id && (
                <Link
                  href={`/check/${refusal.check_id}`}
                  className="mt-3 inline-block text-xs font-medium text-neon-500 hover:underline"
                >
                  View that report →
                </Link>
              )}
            </Card>
          )}

          {refusal.recheck_id && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink">Your re-check</h2>
              <p className="mt-1 text-xs text-muted">
                You have already started a re-check against this refusal.
              </p>
              <Link
                href={`/check/${refusal.recheck_id}`}
                className="mt-2 inline-block text-xs font-medium text-neon-500 hover:underline"
              >
                Open it →
              </Link>
            </Card>
          )}

          <Card className="p-5">
            <h2 className="text-sm font-semibold text-ink">Important</h2>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              This is a reading of your refusal form mapped to document requirements — not
              legal advice, and not a prediction about a future application. The appeal
              deadline and the authority to appeal to are printed on your own letter, and
              those govern.
            </p>
            {plan?.source && (
              <a
                href={plan.source}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-2 inline-block text-xs font-medium text-neon-500 hover:underline"
              >
                The regulation these grounds come from →
              </a>
            )}
          </Card>
        </aside>
      </div>
    </div>
  );
}

function StepCard({ step, index }: { step: PlanStep; index: number }) {
  return (
    <Card className="overflow-hidden">
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
              step.fixable
                ? "border-warn/30 bg-warn/10 text-warn"
                : "border-critical/30 bg-critical/10 text-critical"
            }`}
          >
            Ground {step.ground_number}
          </span>
          <div className="min-w-0">
            <h3 className="font-semibold leading-snug text-ink">
              {index}. {step.title}
            </h3>
            <p className="mt-1.5 text-sm italic leading-relaxed text-muted">
              “{step.official}”
            </p>
            {step.evidence && (
              <p className="mt-2 rounded border border-line bg-white/5 px-2.5 py-1.5 font-mono text-xs text-muted">
                Matched in your letter: {step.evidence.slice(0, 200)}
              </p>
            )}
          </div>
        </div>
      </div>

      <div
        className={`border-l-2 px-4 py-3 ${
          step.fixable ? "border-good bg-good/5" : "border-critical bg-critical/5"
        }`}
      >
        <p className="text-sm leading-relaxed text-ink">
          <span className="font-semibold">
            {step.fixable ? "What to do: " : "Why reapplying will not help: "}
          </span>
          {step.action}
        </p>
        {step.appeal_note && (
          <p className="mt-2 text-sm leading-relaxed text-warn">{step.appeal_note}</p>
        )}
      </div>

      {(step.documents.length > 0 || step.rules.length > 0) && (
        <div className="border-t border-line px-4 py-3">
          {step.documents.length > 0 && (
            <>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">
                Documents this ground touches
              </p>
              <ul className="mt-2 space-y-1.5">
                {step.documents.map((d) => (
                  <li key={d.key} className="text-sm">
                    <span className="font-medium text-ink">{d.label}</span>
                    {d.fix && <span className="text-muted"> — {d.fix}</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {step.rules.length > 0 && (
            <>
              <p
                className={`text-xs font-semibold uppercase tracking-wide text-muted ${
                  step.documents.length ? "mt-3" : ""
                }`}
              >
                Checks that will confirm it
              </p>
              <ul className="mt-2 space-y-1.5">
                {step.rules.map((r) => (
                  <li key={r.id} className="text-sm text-muted">
                    {r.title ?? r.id}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </Card>
  );
}
