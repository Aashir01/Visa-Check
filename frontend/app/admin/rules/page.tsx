"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  Input,
  Loading,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Corridor, RulePack, RulePackSummary } from "@/lib/types";

type Tab = "checklist" | "rules" | "thresholds" | "json";

interface DocSpec {
  key: string;
  label?: string;
  required?: boolean;
  severity?: string;
  why?: string;
  fix?: string;
  profiles?: string[];
  satisfied_by?: string[];
  recommend_if_missing?: boolean;
}

interface RuleSpec {
  id: string;
  type: string;
  severity?: string;
  title?: string;
  fix?: string;
  enabled?: boolean;
  profiles?: string[];
  params?: Record<string, unknown>;
}

export default function AdminRulesPage() {
  const [corridors, setCorridors] = useState<Corridor[] | null>(null);
  const [corridorId, setCorridorId] = useState("");
  const [packs, setPacks] = useState<RulePackSummary[]>([]);
  const [packId, setPackId] = useState("");
  const [pack, setPack] = useState<RulePack | null>(null);

  const [draft, setDraft] = useState<Record<string, unknown> | null>(null);
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("checklist");

  const [errors, setErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newVersion, setNewVersion] = useState("");

  // ---------------- loading ----------------

  useEffect(() => {
    api.admin
      .corridors()
      .then((list) => {
        setCorridors(list);
        setCorridorId((c) => c || list[0]?.id || "");
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const loadPacks = useCallback(async (cid: string, preferred?: string) => {
    const list = await api.admin.rulepacks(cid);
    setPacks(list);
    const pick = preferred ?? list.find((p) => p.is_active)?.id ?? list[0]?.id ?? "";
    setPackId(pick);
    return pick;
  }, []);

  useEffect(() => {
    if (!corridorId) return;
    loadPacks(corridorId).catch((e: Error) => setError(e.message));
  }, [corridorId, loadPacks]);

  useEffect(() => {
    if (!packId) {
      setPack(null);
      setDraft(null);
      return;
    }
    api.admin
      .rulepack(packId)
      .then((p) => {
        setPack(p);
        setDraft(p.data);
        setJsonText(JSON.stringify(p.data, null, 2));
        setErrors([]);
        setNotice(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [packId]);

  // ---------------- editing ----------------

  const isPublished = pack?.status === "published";
  const readOnly = isPublished;

  const documents = useMemo(() => (draft?.documents as DocSpec[]) ?? [], [draft]);
  const rules = useMemo(() => (draft?.rules as RuleSpec[]) ?? [], [draft]);

  function mutate(updater: (d: Record<string, unknown>) => void) {
    setDraft((current) => {
      if (!current) return current;
      const next = structuredClone(current);
      updater(next);
      setJsonText(JSON.stringify(next, null, 2));
      return next;
    });
    setNotice(null);
  }

  function applyJson() {
    try {
      const parsed = JSON.parse(jsonText) as Record<string, unknown>;
      setDraft(parsed);
      setJsonError(null);
      setNotice("JSON applied to the editor. Validate and save to persist it.");
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : "Invalid JSON");
    }
  }

  async function validate() {
    if (!draft) return;
    setBusy(true);
    try {
      const res = await api.admin.validateRulepack(draft);
      setErrors(res.errors);
      setNotice(res.valid ? "This rule pack is valid." : null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Validation failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft() {
    if (!draft || !pack) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.admin.updateRulepack(pack.id, { data: draft });
      setPack(updated);
      setErrors([]);
      setNotice("Draft saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save.");
    } finally {
      setBusy(false);
    }
  }

  async function createVersion(publish: boolean) {
    if (!draft || !corridorId) return;
    const version = newVersion.trim();
    if (!version) {
      setError("Enter a version number for the new rule pack.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.admin.createRulepack(corridorId, {
        version,
        data: draft,
        notes: `Created from ${pack?.version ?? "scratch"}`,
        unverified: Boolean(pack?.unverified ?? true),
        publish,
      });
      setNewVersion("");
      await loadPacks(corridorId, created.id);
      setNotice(
        publish
          ? `Version ${version} created and published. New checks will use it; existing reports keep their own version.`
          : `Version ${version} created as a draft.`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the version.");
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (!pack) return;
    setBusy(true);
    setError(null);
    try {
      await api.admin.publishRulepack(pack.id);
      await loadPacks(corridorId, pack.id);
      setNotice("Published. New checks will use this version.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not publish.");
    } finally {
      setBusy(false);
    }
  }

  if (!corridors && !error) return <Loading />;

  return (
    <div className="container-page py-8">
      <div className="mb-6">
        <h1 className="text-xl font-bold tracking-tight text-ink">Rule packs</h1>
        <p className="mt-0.5 text-sm text-muted">
          The checklist, thresholds and photo specs for each corridor. This is the product.
        </p>
      </div>

      {error && (
        <div className="mb-4">
          <Alert tone="error">{error}</Alert>
        </div>
      )}
      {notice && (
        <div className="mb-4">
          <Alert tone="success">{notice}</Alert>
        </div>
      )}

      {/* ---------------- selectors ---------------- */}
      <Card className="mb-4 p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Corridor">
            <Select value={corridorId} onChange={(e) => setCorridorId(e.target.value)}>
              {corridors?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Version">
            <Select value={packId} onChange={(e) => setPackId(e.target.value)}>
              {packs.map((p) => (
                <option key={p.id} value={p.id}>
                  v{p.version} — {p.status}
                  {p.is_active ? " (live)" : ""}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        {pack && (
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
            <Badge
              className={
                pack.status === "published"
                  ? "border-good/25 bg-good/10 text-good"
                  : pack.status === "draft"
                    ? "border-neon-500/25 bg-neon-500/10 text-neon-500"
                    : "border-line bg-white/5 text-muted"
              }
            >
              {pack.status}
            </Badge>
            {pack.unverified && (
              <Badge className="border-amber-400/40 bg-amber-50 text-amber-800">
                unverified
              </Badge>
            )}
            <span className="text-xs text-muted">
              created {formatDateTime(pack.created_at)}
              {pack.published_at && ` · published ${formatDateTime(pack.published_at)}`}
            </span>
          </div>
        )}
      </Card>

      {readOnly && (
        <div className="mb-4">
          <Alert tone="info" title="Published packs are read-only">
            Reports must stay reproducible, so a published version can never be edited.
            Change what you need below, then save it as a new version — existing reports
            keep the version they ran against.
          </Alert>
        </div>
      )}

      {errors.length > 0 && (
        <div className="mb-4">
          <Alert tone="error" title={`${errors.length} problem(s) found`}>
            <ul className="mt-1 list-inside list-disc space-y-0.5">
              {errors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </Alert>
        </div>
      )}

      {draft && (
        <>
          {/* ---------------- tabs ---------------- */}
          <div className="mb-4 flex gap-1 border-b border-line">
            {(
              [
                ["checklist", `Checklist (${documents.length})`],
                ["rules", `Rules (${rules.length})`],
                ["thresholds", "Metadata & FX"],
                ["json", "Raw JSON"],
              ] as [Tab, string][]
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
                  tab === key
                    ? "border-neon-500 text-neon-500"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "checklist" && (
            <ChecklistEditor documents={documents} readOnly={readOnly} mutate={mutate} />
          )}
          {tab === "rules" && (
            <RulesEditor rules={rules} readOnly={readOnly} mutate={mutate} />
          )}
          {tab === "thresholds" && (
            <MetadataEditor draft={draft} readOnly={readOnly} mutate={mutate} />
          )}
          {tab === "json" && (
            <Card className="p-4">
              <Field
                label="Rule pack JSON"
                hint="Edit directly, then apply. Validation runs against the same schema the engine uses."
                error={jsonError ?? undefined}
              >
                <Textarea
                  value={jsonText}
                  onChange={(e) => setJsonText(e.target.value)}
                  rows={26}
                  spellCheck={false}
                  className="font-mono text-xs"
                />
              </Field>
              <Button variant="secondary" onClick={applyJson} className="mt-3">
                Apply JSON to editor
              </Button>
            </Card>
          )}

          {/* ---------------- actions ---------------- */}
          <Card className="mt-6 p-4">
            <div className="flex flex-wrap items-end gap-3">
              <Button variant="secondary" onClick={validate} disabled={busy}>
                {busy && <Spinner />} Validate
              </Button>

              {!readOnly && (
                <>
                  <Button onClick={saveDraft} disabled={busy}>
                    Save draft
                  </Button>
                  <Button variant="secondary" onClick={publish} disabled={busy}>
                    Publish this version
                  </Button>
                </>
              )}

              <div className="ml-auto flex items-end gap-2">
                <div className="w-40">
                  <Field label="New version">
                    <Input
                      value={newVersion}
                      onChange={(e) => setNewVersion(e.target.value)}
                      placeholder="0.2.0"
                    />
                  </Field>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => void createVersion(false)}
                  disabled={busy}
                >
                  Save as new draft
                </Button>
                <Button onClick={() => void createVersion(true)} disabled={busy}>
                  Save &amp; publish
                </Button>
              </div>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

// --------------------------------------------------------------------------
// checklist
// --------------------------------------------------------------------------

function ChecklistEditor({
  documents,
  readOnly,
  mutate,
}: {
  documents: DocSpec[];
  readOnly: boolean;
  mutate: (fn: (d: Record<string, unknown>) => void) => void;
}) {
  function update(index: number, patch: Partial<DocSpec>) {
    mutate((d) => {
      const docs = d.documents as DocSpec[];
      docs[index] = { ...docs[index], ...patch };
    });
  }

  return (
    <div className="space-y-3">
      {documents.map((doc, i) => (
        <Card key={`${doc.key}-${i}`} className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink">{doc.label ?? doc.key}</span>
              <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-muted">
                {doc.key}
              </code>
            </div>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={Boolean(doc.required)}
                  disabled={readOnly}
                  onChange={(e) => update(i, { required: e.target.checked })}
                  className="h-4 w-4 rounded border-line text-neon-500"
                />
                Required
              </label>
              <div className="w-32">
                <Select
                  value={doc.severity ?? "critical"}
                  disabled={readOnly}
                  onChange={(e) => update(i, { severity: e.target.value })}
                  className="text-xs"
                  aria-label={`Severity for ${doc.key}`}
                >
                  <option value="critical">critical</option>
                  <option value="warning">warning</option>
                  <option value="info">info</option>
                </Select>
              </div>
            </div>
          </div>

          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Why it is needed">
              <Textarea
                value={doc.why ?? ""}
                disabled={readOnly}
                onChange={(e) => update(i, { why: e.target.value })}
                rows={3}
                className="text-sm"
              />
            </Field>
            <Field label="How to fix (shown to the applicant)">
              <Textarea
                value={doc.fix ?? ""}
                disabled={readOnly}
                onChange={(e) => update(i, { fix: e.target.value })}
                rows={3}
                className="text-sm"
              />
            </Field>
          </div>

          <p className="mt-2 text-xs text-muted">
            Applies to: {(doc.profiles ?? ["*"]).join(", ")}
            {doc.satisfied_by?.length ? ` · also satisfied by: ${doc.satisfied_by.join(", ")}` : ""}
          </p>
        </Card>
      ))}
    </div>
  );
}

// --------------------------------------------------------------------------
// rules
// --------------------------------------------------------------------------

function RulesEditor({
  rules,
  readOnly,
  mutate,
}: {
  rules: RuleSpec[];
  readOnly: boolean;
  mutate: (fn: (d: Record<string, unknown>) => void) => void;
}) {
  function update(index: number, patch: Partial<RuleSpec>) {
    mutate((d) => {
      const list = d.rules as RuleSpec[];
      list[index] = { ...list[index], ...patch };
    });
  }

  function updateParam(index: number, key: string, raw: string) {
    mutate((d) => {
      const list = d.rules as RuleSpec[];
      const params = { ...(list[index].params ?? {}) };
      // Keep numbers numeric so the engine compares rather than concatenates.
      const asNumber = Number(raw);
      params[key] = raw !== "" && !Number.isNaN(asNumber) ? asNumber : raw;
      list[index] = { ...list[index], params };
    });
  }

  return (
    <div className="space-y-3">
      {rules.map((rule, i) => {
        const params = rule.params ?? {};
        const scalarParams = Object.entries(params).filter(
          ([, v]) => typeof v === "number" || typeof v === "string",
        );

        return (
          <Card key={rule.id} className="p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold text-ink">{rule.title ?? rule.id}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-muted">
                    {rule.id}
                  </code>
                  <Badge className="border-line bg-white/5 text-muted">{rule.type}</Badge>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 text-sm">
                  <input
                    type="checkbox"
                    checked={rule.enabled !== false}
                    disabled={readOnly}
                    onChange={(e) => update(i, { enabled: e.target.checked })}
                    className="h-4 w-4 rounded border-line text-neon-500"
                  />
                  Enabled
                </label>
                <div className="w-32">
                  <Select
                    value={rule.severity ?? "warning"}
                    disabled={readOnly}
                    onChange={(e) => update(i, { severity: e.target.value })}
                    className="text-xs"
                    aria-label={`Severity for ${rule.id}`}
                  >
                    <option value="critical">critical</option>
                    <option value="warning">warning</option>
                    <option value="info">info</option>
                  </Select>
                </div>
              </div>
            </div>

            {scalarParams.length > 0 && (
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                {scalarParams.map(([key, value]) => (
                  <Field key={key} label={key.replace(/_/g, " ")}>
                    <Input
                      value={String(value)}
                      disabled={readOnly}
                      onChange={(e) => updateParam(i, key, e.target.value)}
                      className="text-sm"
                    />
                  </Field>
                ))}
              </div>
            )}

            {Object.entries(params).some(([, v]) => typeof v === "object") && (
              <p className="mt-2 text-xs text-muted">
                This rule has structured parameters (lists or objects). Edit those on the
                Raw JSON tab.
              </p>
            )}

            <Field label="How to fix (shown to the applicant)">
              <Textarea
                value={rule.fix ?? ""}
                disabled={readOnly}
                onChange={(e) => update(i, { fix: e.target.value })}
                rows={2}
                className="mt-2 text-sm"
              />
            </Field>
          </Card>
        );
      })}
    </div>
  );
}

// --------------------------------------------------------------------------
// metadata
// --------------------------------------------------------------------------

function MetadataEditor({
  draft,
  readOnly,
  mutate,
}: {
  draft: Record<string, unknown>;
  readOnly: boolean;
  mutate: (fn: (d: Record<string, unknown>) => void) => void;
}) {
  const fx = (draft.fx as { base?: string; updated?: string; rates?: Record<string, number> }) ?? {};
  const weights = (draft.severity_weights as Record<string, number>) ?? {};
  const notes = (draft.source_notes as string[]) ?? [];

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <h2 className="font-semibold text-ink">Pack metadata</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Field label="Title">
            <Input
              value={String(draft.title ?? "")}
              disabled={readOnly}
              onChange={(e) => mutate((d) => void (d.title = e.target.value))}
            />
          </Field>
          <Field label="Effective date">
            <Input
              value={String(draft.effective_date ?? "")}
              disabled={readOnly}
              onChange={(e) => mutate((d) => void (d.effective_date = e.target.value))}
            />
          </Field>
          <Field label="Currency" hint="Thresholds in this pack are expressed here.">
            <Input
              value={String(draft.currency ?? "")}
              disabled={readOnly}
              onChange={(e) => mutate((d) => void (d.currency = e.target.value))}
            />
          </Field>
          <Field label="Default trip length (days)" hint="Used when no travel dates are known.">
            <Input
              type="number"
              value={String(draft.default_trip_days ?? "")}
              disabled={readOnly}
              onChange={(e) =>
                mutate((d) => void (d.default_trip_days = Number(e.target.value)))
              }
            />
          </Field>
        </div>

        <Field label="Disclaimer (printed on every report)">
          <Textarea
            value={String(draft.disclaimer ?? "")}
            disabled={readOnly}
            onChange={(e) => mutate((d) => void (d.disclaimer = e.target.value))}
            rows={3}
            className="mt-3 text-sm"
          />
        </Field>
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold text-ink">Severity weights</h2>
        <p className="mt-1 text-sm text-muted">
          Points deducted from 100 for the first issue of each severity. Later issues of
          the same severity are damped.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          {(["critical", "warning", "info"] as const).map((sev) => (
            <Field key={sev} label={sev}>
              <Input
                type="number"
                value={String(weights[sev] ?? "")}
                disabled={readOnly}
                onChange={(e) =>
                  mutate((d) => {
                    const w = { ...((d.severity_weights as Record<string, number>) ?? {}) };
                    w[sev] = Number(e.target.value);
                    d.severity_weights = w;
                  })
                }
              />
            </Field>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold text-ink">Exchange rates</h2>
        <p className="mt-1 text-sm text-muted">
          Indicative only, used to compare a statement balance against a threshold in a
          different currency. Base: <strong>{fx.base ?? "—"}</strong>
          {fx.updated && ` · updated ${fx.updated}`}. One unit of the base equals the value
          shown.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(fx.rates ?? {}).map(([code, rate]) => (
            <Field key={code} label={code}>
              <Input
                type="number"
                step="any"
                value={String(rate)}
                disabled={readOnly}
                onChange={(e) =>
                  mutate((d) => {
                    const current = (d.fx as { rates?: Record<string, number> }) ?? {};
                    d.fx = {
                      ...current,
                      rates: { ...(current.rates ?? {}), [code]: Number(e.target.value) },
                    };
                  })
                }
              />
            </Field>
          ))}
        </div>
      </Card>

      {notes.length > 0 && (
        <Card className="bg-amber-50/50 p-4">
          <h2 className="font-semibold text-ink">Source notes</h2>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-muted">
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
