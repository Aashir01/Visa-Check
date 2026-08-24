"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { DiffPanel } from "@/components/diff";
import { ScanIcon } from "@/components/icons";
import { CHECK_STEPS, PageHeader } from "@/components/page-header";
import { TimelinePanel } from "@/components/timeline";
import {
  Alert,
  Badge,
  Button,
  Card,
  DraftPackNotice,
  EmptyState,
  Loading,
  LinkButton,
  ScoreGauge,
  Spinner,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import {
  SEVERITY_STYLE,
  TIMELINE_STYLE,
  confidenceLabel,
  formatDate,
  formatDateTime,
  formatEvidenceValue,
  titleCase,
} from "@/lib/format";
import type { AiStatus, Authority, Check, Issue, Severity } from "@/lib/types";

/** Tell the user whether a finding rests on law or on our own judgement. */
const AUTHORITY_LABEL: Record<Authority, string> = {
  law: "This is a legal requirement.",
  member_state: "This figure is published by the destination country.",
  official_guidance: "Based on published official guidance.",
  heuristic: "Our own guidance, not an official requirement.",
};

const GROUPS: { severity: Severity; heading: string; blurb: string }[] = [
  {
    severity: "critical",
    heading: "Critical — fix before submitting",
    blurb: "These are the issues most likely to cause a refusal or a rejected submission.",
  },
  {
    severity: "warning",
    heading: "Warnings — likely to cause questions or delay",
    blurb: "Not automatically fatal, but each one gives the officer a reason to doubt the file.",
  },
  {
    severity: "info",
    heading: "Informational — worth improving",
    blurb: "Optional improvements that strengthen the application.",
  },
];

export default function ReportPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const checkId = params.id;

  const router = useRouter();
  const [check, setCheck] = useState<Check | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [rechecking, setRechecking] = useState(false);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.getCheck(checkId);
      setCheck(data);
      // Poll while the background worker is running.
      if (data.status === "queued" || data.status === "processing") {
        pollRef.current = setTimeout(() => void load(), 1800);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load this report.");
    }
  }, [checkId]);

  useEffect(() => {
    if (!user) return;
    void load();
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, [user, load]);

  async function download() {
    setDownloading(true);
    try {
      const blob = await api.downloadReport(checkId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `visaguard-report-${checkId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not download the report.");
    } finally {
      setDownloading(false);
    }
  }

  /**
   * A new check rather than a re-run: the original report has to survive
   * untouched, because the applicant may already have acted on it — and the
   * comparison between the two is the point.
   */
  async function startRecheck() {
    setRechecking(true);
    try {
      const child = await api.recheck(checkId, { refusal_id: check?.refusal_id ?? null });
      router.push(`/check/${child.id}/upload`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start a re-check.");
      setRechecking(false);
    }
  }

  if (authLoading || (!check && !error)) return <Loading />;

  if (error) {
    return (
      <div className="container-narrow py-10">
        <Alert tone="error" title="Could not load this report">
          {error}
        </Alert>
      </div>
    );
  }
  if (!check) return null;

  // ---------------- in-flight states ----------------
  if (check.status === "queued" || check.status === "processing") {
    return (
      <div className="container-narrow py-20">
        <Card className="p-10 text-center">
          <span className="mx-auto flex h-14 w-14 animate-pulse-glow items-center justify-center rounded-2xl border border-neon-500/25 bg-neon-500/10 text-neon-400">
            <ScanIcon className="h-6 w-6" />
          </span>
          <h1 className="mt-5 font-display text-xl font-semibold text-ink">
            Analysing your documents
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted">
            Reading each file, working out what it is, extracting the fields, then running
            every rule for this corridor. This usually takes under a minute.
          </p>

          {/* Naming the stages makes a silent minute feel like progress rather
              than a hang, without inventing a percentage we cannot measure. */}
          <ol className="mx-auto mt-7 max-w-xs space-y-2.5 text-left">
            {[
              "Decrypting and reading each file",
              "Detecting document types",
              "Extracting names, dates and amounts",
              "Running the corridor rule pack",
            ].map((stage) => (
              <li key={stage} className="flex items-center gap-2.5 text-sm text-muted">
                <Spinner className="h-3.5 w-3.5 shrink-0 text-neon-400" />
                {stage}
              </li>
            ))}
          </ol>

          <p className="mt-7 text-xs text-muted-soft">
            You can leave this page — the report will be waiting under Your checks.
          </p>
        </Card>
      </div>
    );
  }

  if (check.status === "failed") {
    return (
      <div className="container-narrow py-10">
        <Alert tone="error" title="This check could not be completed">
          {check.error ?? "An unexpected error occurred."}
        </Alert>
        <div className="mt-4 flex gap-3">
          <LinkButton href={`/check/${check.id}/upload`} variant="secondary">
            Back to documents
          </LinkButton>
          <LinkButton href="/check/new">Start a new check</LinkButton>
        </div>
      </div>
    );
  }

  if (check.status === "draft") {
    return (
      <div className="container-narrow py-10">
        <EmptyState
          title="This check has not been run yet"
          action={
            <LinkButton href={`/check/${check.id}/upload`}>Upload documents</LinkButton>
          }
        >
          Upload your documents and run the analysis to see a report.
        </EmptyState>
      </div>
    );
  }

  // ---------------- report ----------------
  const issues = check.issues ?? [];
  const extraction = check.extraction ?? {};
  const scoring = extraction.scoring;
  const passed = extraction.passed ?? [];
  const skipped = extraction.skipped ?? [];
  const score = check.risk_score ?? 0;
  const timeline = extraction.timeline ?? [];
  const expiring = timeline.filter(
    (t) => t.status === "expired" || t.status === "expiring",
  );

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ href: "/checks", label: "Your checks" }, { label: "Report" }]}
        title="Document completeness report"
        lede={
          <>
            {check.corridor_label} · {titleCase(check.applicant_profile)}
            <span className="mt-1 block text-sm text-muted-soft">
              Checklist{" "}
              <span className="font-mono">
                {check.pack_meta?.version ?? check.rulepack_version}
              </span>
              {check.pack_meta?.effective_date && <> dated {check.pack_meta.effective_date}</>}
              {" · "}run {formatDateTime(check.completed_at ?? check.created_at)}
            </span>
          </>
        }
        steps={CHECK_STEPS}
        currentStep={2}
        actions={
          <>
            <Button variant="secondary" onClick={download} loading={downloading}>
              Download PDF
            </Button>
            <Button
              variant="neon"
              onClick={startRecheck}
              loading={rechecking}
              title="Confirming the fixes we asked for does not cost another check."
            >
              Fix and re-check — free
            </Button>
          </>
        }
      />

    <div className="container-page py-8 lg:py-10">

      {/*
        The single most urgent thing on this page when it applies: a document
        that is fine today and stale on the day it is handed in.
      */}
      {expiring.length > 0 && (
        <div className="mb-6">
          <Alert
            tone={expiring.some((t) => t.status === "expired") ? "error" : "warning"}
            title="Something in this file goes out of date before your appointment"
          >
            <ul className="mt-1 space-y-1">
              {expiring.map((t) => (
                <li key={`${t.document_type}.${t.field}`}>
                  <strong className={TIMELINE_STYLE[t.status].text}>{t.what}</strong> —{" "}
                  {formatDate(t.valid_until)}
                  {t.days_remaining != null && t.days_remaining < 0
                    ? ` (${Math.abs(t.days_remaining)} day(s) before you submit)`
                    : t.days_remaining != null
                      ? ` (${t.days_remaining} day(s) spare)`
                      : ""}
                </li>
              ))}
            </ul>
          </Alert>
        </div>
      )}

      {check.diff && (
        <div className="mb-6">
          <DiffPanel diff={check.diff} />
        </div>
      )}

      {check.rulepack_unverified && (
        <div className="mb-6">
          <DraftPackNotice version={check.pack_meta?.version ?? check.rulepack_version} />
        </div>
      )}

      {/* score */}
      <Card className="mb-6 flex flex-col items-center gap-8 p-6 sm:flex-row sm:items-start sm:p-7">
        <ScoreGauge score={score} band={check.risk_band} size={170} />

        <div className="min-w-0 flex-1">
          <h2 className="font-display text-xl font-semibold text-ink-strong">
            {scoring?.band_label ?? "Result"}
          </h2>
          <p className="mt-1 leading-relaxed text-muted">{scoring?.band_message}</p>

          <div className="mt-4 flex flex-wrap gap-2">
            {(["critical", "warning", "info"] as Severity[]).map((sev) => (
              <Badge key={sev} className={SEVERITY_STYLE[sev].chip}>
                {scoring?.counts?.[sev] ?? 0} {SEVERITY_STYLE[sev].label.toLowerCase()}
              </Badge>
            ))}
            <Badge className="border-good/25 bg-good/10 text-good">
              {passed.length} passed
            </Badge>
            {skipped.length > 0 && (
              <Badge className="border-line bg-white/5 text-muted">
                {skipped.length} not evaluated
              </Badge>
            )}
          </div>

          {check.summary && (
            <p className="mt-4 text-sm leading-relaxed text-ink">{check.summary}</p>
          )}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        {/* ---------------- issues ---------------- */}
        <div className="space-y-8">
          {issues.length === 0 ? (
            <Card className="p-6">
              <h2 className="font-semibold text-good">No issues detected</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                Nothing on checklist{" "}
                <span className="font-mono">{check.pack_meta?.version}</span> was found
                missing or inconsistent in the documents you uploaded. This is not a
                prediction of approval — it means the checklist found no problems.
              </p>
            </Card>
          ) : (
            GROUPS.map((group) => {
              const rows = issues.filter((i) => i.severity === group.severity);
              if (!rows.length) return null;
              return (
                <section key={group.severity}>
                  <h2 className={`font-semibold ${SEVERITY_STYLE[group.severity].text}`}>
                    {group.heading}
                  </h2>
                  <p className="mt-0.5 text-sm text-muted">{group.blurb}</p>
                  <div className="mt-4 space-y-3">
                    {rows.map((issue, index) => (
                      <IssueCard key={issue.id} issue={issue} index={index + 1} />
                    ))}
                  </div>
                </section>
              );
            })
          )}

          {timeline.length > 0 && (
            <TimelinePanel
              timeline={timeline}
              submissionDate={extraction.submission_date ?? check.submission_date}
              source={extraction.submission_date_source}
            />
          )}

          {skipped.length > 0 && (
            <section>
              <h2 className="font-semibold text-ink">Checks that could not be run</h2>
              <p className="mt-0.5 text-sm text-muted">
                These depend on a document that was missing, or a field that could not be
                read. <strong className="text-ink">They did not pass</strong> — they were
                not checked. Verify them yourself before submitting.
              </p>
              <Card className="mt-3 divide-y divide-line">
                {skipped.map((s) => (
                  <div key={s.rule_id} className="flex items-start gap-2.5 px-4 py-2.5">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-white/20" />
                    <span className="text-sm text-ink">{s.title}</span>
                  </div>
                ))}
              </Card>
            </section>
          )}
        </div>

        {/* ---------------- sidebar ---------------- */}
        <aside className="space-y-4">
          <Card className="p-5">
            <h2 className="text-sm font-semibold text-ink">Documents analysed</h2>
            <ul className="mt-3 space-y-3">
              {check.documents.map((doc) => {
                const conf = confidenceLabel(doc.doc_type_confidence);
                return (
                  <li key={doc.id} className="text-sm">
                    <p className="truncate font-medium text-ink" title={doc.filename}>
                      {doc.filename}
                    </p>
                    <p className="text-xs text-muted">
                      {doc.doc_type_label ?? "Unrecognised"} ·{" "}
                      <span className={conf.tone}>
                        {doc.doc_type_source === "user" ? "set by you" : `${conf.label} confidence`}
                      </span>
                    </p>
                  </li>
                );
              })}
            </ul>
          </Card>

          {passed.length > 0 && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink">
                Verified ({passed.length})
              </h2>
              <ul className="mt-3 space-y-2">
                {passed.map((p) => (
                  <li key={p.rule_id} className="flex items-start gap-2 text-sm">
                    <svg
                      viewBox="0 0 20 20"
                      className="mt-0.5 h-3.5 w-3.5 shrink-0 fill-good"
                      aria-hidden
                    >
                      <path d="M8.3 13.6 4.7 10l1.3-1.3 2.3 2.3 5.7-5.7L15.3 6.6z" />
                    </svg>
                    <span className="text-muted">{p.title}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <AiStatusNotice status={extraction.ai_status} degraded={extraction.degraded_llm} />

          {!check.refusal_id && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink">Already been refused?</h2>
              <p className="mt-2 text-xs leading-relaxed text-muted">
                A Schengen refusal comes on a standard form with eleven numbered grounds.
                Upload it and we will decode which ones you were given, whether reapplying
                can answer them, and what to change first.
              </p>
              <Link
                href={`/refusals/new?check=${check.id}&corridor=${check.corridor_id}`}
                className="mt-3 inline-block text-xs font-medium text-neon-500 hover:underline"
              >
                Decode a refusal letter →
              </Link>
            </Card>
          )}

          <Card className="bg-white/5 p-5">
            <h2 className="text-sm font-semibold text-ink">Important</h2>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              {check.pack_meta?.disclaimer}
              {" "}This report reflects checklist{" "}
              <span className="font-mono">{check.pack_meta?.version}</span>. Consular
              requirements change without notice and vary between consulates and individual
              cases. Nothing here predicts the outcome of an application.
            </p>
          </Card>

          <p className="px-1 text-xs text-muted">
            <Link href="/checks" className="font-medium text-neon-500 hover:underline">
              ← All checks
            </Link>
          </p>
        </aside>
      </div>
    </div>
    </div>
  );
}

function IssueCard({ issue, index }: { issue: Issue; index: number }) {
  const style = SEVERITY_STYLE[issue.severity];
  const evidence = issue.evidence.filter((e) => e.value != null);
  const lowConfidence = issue.confidence < 0.6;

  return (
    <Card className="overflow-hidden">
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span
            className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.chip}`}
          >
            {style.label}
          </span>
          <div className="min-w-0">
            <h3 className="font-semibold leading-snug text-ink">
              {index}. {issue.title}
            </h3>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{issue.detail}</p>
          </div>
        </div>

        {evidence.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5 pl-0 sm:pl-[4.75rem]">
            {evidence.slice(0, 6).map((e, i) => (
              <span
                key={i}
                className="rounded border border-line bg-white/5 px-2 py-1 text-xs text-muted"
              >
                {e.document_label && <span className="text-ink">{e.document_label}</span>}
                {e.field && <> · {e.field.replace(/_/g, " ")}</>}
                {": "}
                <span className="font-medium text-ink">
                  {formatEvidenceValue(e.value).slice(0, 80)}
                </span>
              </span>
            ))}
          </div>
        )}
      </div>

      {issue.fix && (
        <div className="border-l-2 border-good bg-good/10 px-4 py-3">
          <p className="text-sm leading-relaxed text-ink">
            <span className="font-semibold">How to fix: </span>
            {issue.fix}
          </p>
        </div>
      )}

      {(issue.authority || lowConfidence) && (
        <div className="border-t border-line px-4 py-2 text-xs text-muted">
          {issue.authority && (
            <p>
              <span className="font-medium text-ink">{AUTHORITY_LABEL[issue.authority]}</span>
              {issue.sources?.[0] && (
                <>
                  {" "}
                  <a
                    href={issue.sources[0]}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-neon-500 underline"
                  >
                    Source
                  </a>
                </>
              )}
            </p>
          )}
          {lowConfidence && (
            <p className={issue.authority ? "mt-1" : undefined}>
              Lower confidence finding — please verify this yourself before acting on it.
            </p>
          )}
        </div>
      )}
    </Card>
  );
}


/**
 * Explain the absence of the AI review precisely. "Not included on your plan"
 * and "we tried and it broke" are very different things to be told about a
 * document that decides whether you travel.
 */
function AiStatusNotice({
  status,
  degraded,
}: {
  status?: AiStatus;
  degraded?: boolean;
}) {
  if (status === "included" || status === "not_applicable") return null;
  if (!status && !degraded) return null;

  if (status === "not_in_tier") {
    return (
      <Alert tone="info" title="This was a free check">
        <p>
          Every checklist, identity, financial, date and photo rule ran on your
          documents. What a full check adds is an AI review of your letters —
          whether your invitation letter names who is paying, whether your
          employment letter confirms approved leave.
        </p>
        <p className="mt-2">
          <Link href="/account" className="font-medium underline">
            See your options
          </Link>
        </p>
      </Alert>
    );
  }

  if (status === "budget_exhausted") {
    return (
      <Alert tone="warning" title="AI review stopped early">
        This check reached its cost limit part-way through the letter review, so
        those findings may be incomplete. Every checklist, identity, financial and
        photo check still ran.
      </Alert>
    );
  }

  return (
    <Alert tone="warning" title="AI review was unavailable">
      Letter-content findings are not included in this report. Every checklist,
      identity, financial and photo check still ran.
    </Alert>
  );
}
