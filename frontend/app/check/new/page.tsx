"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { CheckCircleIcon, ClockIcon, LockIcon } from "@/components/icons";
import { Picture } from "@/components/media";
import { CHECK_STEPS, PageHeader } from "@/components/page-header";
import {
  Alert,
  Button,
  Card,
  CardHeader,
  Chip,
  DraftPackNotice,
  Field,
  Input,
  Loading,
  Select,
  Skeleton,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { corridorPhoto } from "@/lib/media";
import type { ChecklistPreview, Corridor, Profile } from "@/lib/types";

const PROFILE_HELP: Record<string, string> = {
  employed: "You work for an employer who can issue a letter and approve leave.",
  self_employed: "You own or run a business, or work freelance.",
  student: "You are enrolled at a school, college or university.",
  retired: "You are retired and living on a pension or savings.",
};

function NewCheckInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const [corridors, setCorridors] = useState<Corridor[] | null>(null);
  const [corridorId, setCorridorId] = useState(params.get("corridor") ?? "");
  const [profile, setProfile] = useState<Profile>("employed");
  const [travelFrom, setTravelFrom] = useState("");
  const [travelTo, setTravelTo] = useState("");
  const [submissionDate, setSubmissionDate] = useState("");
  const refusalId = params.get("refusal");

  const [checklist, setChecklist] = useState<ChecklistPreview | null>(null);
  const [checklistLoading, setChecklistLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .corridors()
      .then((list) => {
        setCorridors(list);
        setCorridorId((current) => current || list[0]?.id || "");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!corridorId) return;
    setChecklistLoading(true);
    api
      .checklist(corridorId, profile)
      .then(setChecklist)
      .catch(() => setChecklist(null))
      .finally(() => setChecklistLoading(false));
  }, [corridorId, profile]);

  const corridor = useMemo(
    () => corridors?.find((c) => c.id === corridorId) ?? null,
    [corridors, corridorId],
  );

  const profiles = useMemo(() => {
    const fromPack = corridor?.profiles;
    if (fromPack && Object.keys(fromPack).length) return fromPack;
    return {
      employed: "Employed",
      self_employed: "Self-employed / business owner",
      student: "Student",
      retired: "Retired",
    };
  }, [corridor]);

  const datesInvalid =
    Boolean(travelFrom && travelTo) && new Date(travelTo) < new Date(travelFrom);

  async function onStart() {
    setError(null);

    if (!user) {
      router.push(`/login?next=${encodeURIComponent(`/check/new?corridor=${corridorId}`)}`);
      return;
    }
    if (datesInvalid) {
      setError("Your return date is before your departure date.");
      return;
    }

    setBusy(true);
    try {
      const check = await api.createCheck({
        corridor_id: corridorId,
        applicant_profile: profile,
        travel_from: travelFrom || null,
        travel_to: travelTo || null,
        submission_date: submissionDate || null,
        refusal_id: refusalId,
      });
      router.push(`/check/${check.id}/upload`);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? "This corridor has no published checklist yet."
          : err instanceof Error
            ? err.message
            : "Could not start the check.",
      );
      setBusy(false);
    }
  }

  if (!corridors && !error) return <Loading label="Loading corridors…" />;

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ href: "/", label: "Home" }, { label: "New check" }]}
        title="Start a new check"
        lede="Tell us where you are applying and what your situation is. The checklist below updates as you choose — it is free, and you can read the whole thing before uploading anything."
        steps={CHECK_STEPS}
        currentStep={0}
      />

      <div className="container-page py-8 lg:py-10">
        {refusalId && (
          <div className="mb-6">
            <Alert tone="info" title="This check answers your refusal">
              When it finishes, the report will say — ground by ground — whether the things you
              were refused on are now clear.{" "}
              <Link href={`/refusals/${refusalId}`} className="font-medium">
                Back to the plan
              </Link>
            </Alert>
          </div>
        )}

        {error && (
          <div className="mb-6">
            <Alert tone="error" title="Something went wrong">
              {error}
            </Alert>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,390px)_minmax(0,1fr)] lg:items-start">
          {/* ------------------------------------------------------------ */}
          {/* Form                                                          */}
          {/* ------------------------------------------------------------ */}
          <div className="space-y-4 lg:sticky lg:top-24">
            <Card className="overflow-hidden">
              {/* The destination, shown rather than named. It also confirms
                  the corridor selection at a glance while scrolling. */}
              {corridor && (
                <Picture
                  photo={corridorPhoto(corridor.key)}
                  ratio="21/9"
                  sizes="(min-width: 1024px) 390px, 100vw"
                >
                  <div
                    aria-hidden
                    className="absolute inset-0 bg-gradient-to-t from-surface-card via-surface-card/35 to-transparent"
                  />
                  <div className="absolute inset-x-4 bottom-3">
                    <p className="font-display text-base font-semibold text-white drop-shadow">
                      {corridor.label}
                    </p>
                  </div>
                </Picture>
              )}

              <div className="space-y-5 p-5">
                <Field label="Where are you applying?">
                  <Select value={corridorId} onChange={(e) => setCorridorId(e.target.value)}>
                    {corridors?.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Field label="Your situation" hint={PROFILE_HELP[profile]}>
                  <Select
                    value={profile}
                    onChange={(e) => setProfile(e.target.value as Profile)}
                  >
                    {Object.entries(profiles).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Field>

                <div className="grid grid-cols-2 gap-3">
                  <Field label="Departure" optional>
                    <Input
                      type="date"
                      value={travelFrom}
                      onChange={(e) => setTravelFrom(e.target.value)}
                    />
                  </Field>
                  <Field
                    label="Return"
                    optional
                    error={datesInvalid ? "Before departure" : undefined}
                  >
                    <Input
                      type="date"
                      value={travelTo}
                      onChange={(e) => setTravelTo(e.target.value)}
                      min={travelFrom || undefined}
                    />
                  </Field>
                </div>

                <p className="-mt-1 text-xs leading-relaxed text-muted">
                  Travel dates are optional but strongly recommended — funds thresholds and
                  insurance cover are both calculated from your trip length.
                </p>

                {/*
                  The date that actually decides validity. A statement that is
                  fine today can be three weeks stale at an appointment, and it
                  is the appointment date the consulate applies — so every age
                  limit is measured against this, not against today.
                */}
                <Field
                  label="Appointment date"
                  optional
                  hint="When you will hand the file in. We date every document against this, not against today."
                >
                  <Input
                    type="date"
                    value={submissionDate}
                    onChange={(e) => setSubmissionDate(e.target.value)}
                    min={new Date().toISOString().slice(0, 10)}
                  />
                </Field>

                <Button
                  onClick={onStart}
                  loading={busy}
                  disabled={!corridorId || authLoading}
                  size="lg"
                  className="w-full"
                >
                  {user ? "Continue to upload" : "Sign in to continue"}
                  <span aria-hidden>→</span>
                </Button>

                {!user && !authLoading && (
                  <p className="text-center text-xs leading-relaxed text-muted">
                    The checklist on this page is free.{" "}
                    <Link
                      href="/register"
                      className="font-medium text-neon-400 hover:underline"
                    >
                      Create an account
                    </Link>{" "}
                    to analyse your documents.
                  </p>
                )}

                <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 border-t border-line pt-4 text-[11px] text-muted-soft">
                  <span className="flex items-center gap-1.5">
                    <LockIcon className="h-3 w-3" /> Encrypted at rest
                  </span>
                  <span className="flex items-center gap-1.5">
                    <ClockIcon className="h-3 w-3" /> Purged after 30 days
                  </span>
                </div>
              </div>
            </Card>

            {checklist?.key_thresholds && checklist.key_thresholds.length > 0 && (
              <Card>
                <CardHeader title="Key requirements" subtitle="For the profile you selected." />
                <dl className="divide-y divide-line">
                  {checklist.key_thresholds.map((t) => (
                    <div key={t.label} className="flex justify-between gap-4 px-5 py-3 text-sm">
                      <dt className="text-muted">{t.label}</dt>
                      <dd className="text-right font-medium text-ink">{t.value}</dd>
                    </div>
                  ))}
                </dl>
              </Card>
            )}
          </div>

          {/* ------------------------------------------------------------ */}
          {/* Checklist                                                     */}
          {/* ------------------------------------------------------------ */}
          <div className="space-y-4">
            {corridor?.rulepack_unverified && (
              <DraftPackNotice version={corridor.rulepack_version} />
            )}

            {checklistLoading && (
              <Card className="p-5">
                <div className="space-y-4">
                  <Skeleton className="h-5 w-1/3" />
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="space-y-2 border-t border-line pt-4">
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-3 w-4/5" />
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {checklist && !checklistLoading && (
              <>
                <Card>
                  <CardHeader
                    icon={<CheckCircleIcon className="h-4 w-4" />}
                    title={`Documents you need (${checklist.required_documents.length})`}
                    subtitle="Everything on this list is required for your corridor and profile."
                    action={
                      <Chip className="font-mono text-[11px]">v{checklist.version}</Chip>
                    }
                  />

                  <ul className="divide-y divide-line">
                    {checklist.required_documents.map((doc) => (
                      <li key={doc.key} className="px-5 py-4">
                        <div className="flex items-start gap-3">
                          <span
                            className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${
                              doc.severity === "critical" ? "bg-critical" : "bg-warn"
                            }`}
                            aria-label={doc.severity === "critical" ? "Critical" : "Warning"}
                          />
                          <div className="min-w-0">
                            <p className="font-medium text-ink">{doc.label}</p>
                            {doc.why && (
                              <p className="mt-1 text-sm leading-relaxed text-muted">{doc.why}</p>
                            )}
                            {doc.alternatives.length > 0 && (
                              <p className="mt-1.5 text-xs text-muted-soft">
                                Or: {doc.alternatives.join(", ")}
                              </p>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </Card>

                {checklist.optional_documents.length > 0 && (
                  <Card>
                    <CardHeader
                      title={`Recommended, not required (${checklist.optional_documents.length})`}
                      subtitle="These strengthen an application without being mandatory."
                    />
                    <ul className="space-y-2.5 p-5">
                      {checklist.optional_documents.map((doc) => (
                        <li key={doc.key} className="flex items-start gap-2.5 text-sm">
                          <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-white/25" />
                          <div>
                            <span className="font-medium text-ink">{doc.label}</span>
                            {doc.why && <span className="text-muted"> — {doc.why}</span>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}

                {checklist.disclaimer && (
                  <p className="px-1 text-xs leading-relaxed text-muted-soft">
                    {checklist.disclaimer}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NewCheckPage() {
  return (
    <Suspense fallback={<Loading />}>
      <NewCheckInner />
    </Suspense>
  );
}
