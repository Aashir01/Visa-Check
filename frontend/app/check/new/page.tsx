"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  DraftPackNotice,
  Field,
  Input,
  Loading,
  Select,
  Spinner,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
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
    <div className="container-page py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Start a new check</h1>
        <p className="mt-1 text-muted">
          Tell us where you are applying and your situation. The checklist below updates as
          you choose.
        </p>
      </div>

      {refusalId && (
        <div className="mb-6">
          <Alert tone="info" title="This check answers your refusal">
            When it finishes, the report will say — ground by ground — whether the things
            you were refused on are now clear.{" "}
            <Link href={`/refusals/${refusalId}`} className="font-medium underline">
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

      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        {/* ---------------- form ---------------- */}
        <div className="space-y-4">
          <Card className="space-y-5 p-5">
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
              <Field label="Departure">
                <Input
                  type="date"
                  value={travelFrom}
                  onChange={(e) => setTravelFrom(e.target.value)}
                />
              </Field>
              <Field label="Return" error={datesInvalid ? "Before departure" : undefined}>
                <Input
                  type="date"
                  value={travelTo}
                  onChange={(e) => setTravelTo(e.target.value)}
                  min={travelFrom || undefined}
                />
              </Field>
            </div>

            <p className="-mt-1 text-xs text-muted">
              Travel dates are optional but strongly recommended — funds thresholds and
              insurance cover are both calculated from your trip length.
            </p>

            {/*
              The date that actually decides validity. A statement that is fine
              today can be three weeks stale at an appointment, and it is the
              appointment date the consulate applies — so every age limit is
              measured against this, not against today.
            */}
            <Field
              label="Appointment date"
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
              disabled={busy || !corridorId || authLoading}
              size="lg"
              className="w-full"
            >
              {busy && <Spinner />}
              {user ? "Continue to upload" : "Sign in to continue"}
            </Button>

            {!user && !authLoading && (
              <p className="text-center text-xs text-muted">
                The checklist on this page is free.{" "}
                <Link href="/register" className="font-medium text-neon-500 hover:underline">
                  Create an account
                </Link>{" "}
                to analyse your documents.
              </p>
            )}
          </Card>

          {checklist?.key_thresholds && checklist.key_thresholds.length > 0 && (
            <Card className="p-5">
              <h2 className="text-sm font-semibold text-ink">Key requirements</h2>
              <dl className="mt-3 space-y-2.5">
                {checklist.key_thresholds.map((t) => (
                  <div key={t.label} className="flex justify-between gap-4 text-sm">
                    <dt className="text-muted">{t.label}</dt>
                    <dd className="text-right font-medium text-ink">{t.value}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          )}
        </div>

        {/* ---------------- checklist ---------------- */}
        <div className="space-y-4">
          {corridor?.rulepack_unverified && (
            <DraftPackNotice version={corridor.rulepack_version} />
          )}

          {checklistLoading && <Loading label="Loading checklist…" />}

          {checklist && !checklistLoading && (
            <>
              <Card className="p-5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-semibold text-ink">
                    Documents you need ({checklist.required_documents.length})
                  </h2>
                  <Badge className="border-line bg-white/5 text-muted">
                    checklist v{checklist.version}
                  </Badge>
                </div>

                <ul className="mt-4 divide-y divide-line">
                  {checklist.required_documents.map((doc) => (
                    <li key={doc.key} className="py-3 first:pt-0 last:pb-0">
                      <div className="flex items-start gap-3">
                        <span
                          className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                            doc.severity === "critical" ? "bg-critical" : "bg-warn"
                          }`}
                        />
                        <div className="min-w-0">
                          <p className="font-medium text-ink">{doc.label}</p>
                          {doc.why && (
                            <p className="mt-0.5 text-sm leading-relaxed text-muted">
                              {doc.why}
                            </p>
                          )}
                          {doc.alternatives.length > 0 && (
                            <p className="mt-1 text-xs text-muted">
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
                <Card className="p-5">
                  <h2 className="font-semibold text-ink">
                    Recommended, not required ({checklist.optional_documents.length})
                  </h2>
                  <p className="mt-1 text-sm text-muted">
                    These strengthen an application without being mandatory.
                  </p>
                  <ul className="mt-3 space-y-2">
                    {checklist.optional_documents.map((doc) => (
                      <li key={doc.key} className="flex items-start gap-2 text-sm">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-white/20" />
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
                <p className="px-1 text-xs leading-relaxed text-muted">
                  {checklist.disclaimer}
                </p>
              )}
            </>
          )}
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
