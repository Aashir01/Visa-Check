"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";

import { FormIcon } from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Loading,
  Select,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { formatBytes } from "@/lib/format";
import type { Corridor, RefusalGround } from "@/lib/types";

type Mode = "upload" | "paste" | "pick";

const MODES: { key: Mode; label: string; blurb: string }[] = [
  {
    key: "upload",
    label: "Upload the letter",
    blurb: "The standard refusal form, as a photo or PDF. We read the ticked boxes.",
  },
  {
    key: "paste",
    label: "Paste the text",
    blurb: "If you only have the wording — an email, or a translation you typed out.",
  },
  {
    key: "pick",
    label: "Tick the grounds",
    blurb: "Read the numbers off your own letter and select them. Always exact.",
  },
];

function DecodeInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, loading: authLoading } = useRequireAuth();

  const [mode, setMode] = useState<Mode>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [corridorId, setCorridorId] = useState(params.get("corridor") ?? "");
  const checkId = params.get("check");

  const [corridors, setCorridors] = useState<Corridor[]>([]);
  const [grounds, setGrounds] = useState<RefusalGround[] | null>(null);
  const [source, setSource] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    void api.corridors().then(setCorridors).catch(() => setCorridors([]));
    void api
      .refusalGrounds()
      .then((r) => {
        setGrounds(r.grounds);
        setSource(r.source);
      })
      .catch((e: Error) => setError(e.message));
  }, [user]);

  const ready = useMemo(() => {
    if (mode === "upload") return Boolean(file);
    if (mode === "paste") return text.trim().length > 20;
    return picked.length > 0;
  }, [mode, file, text, picked]);

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      const refusal = await api.createRefusal({
        file: mode === "upload" ? file : null,
        text: mode === "paste" ? text : undefined,
        groundCodes: mode === "pick" ? picked : undefined,
        corridorId: corridorId || null,
        checkId,
      });
      router.push(`/refusals/${refusal.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not decode that refusal.");
      setBusy(false);
    }
  }

  if (authLoading || (!grounds && !error)) return <Loading label="Loading grounds…" />;

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ href: "/refusals", label: "Refusals" }, { label: "Decode" }]}
        title="Decode your refusal"
        lede="A Schengen refusal is not a letter — it is a form. The consulate ticks numbered boxes from a list of eleven, identical in every member state. That makes the reason readable, once you know what the numbers mean. Give us the form and we will tell you which grounds you were given, whether reapplying can answer them, and what to change first."
      />

      <div className="container-page py-8 lg:py-10">
      {error && (
        <div className="mb-6 max-w-2xl">
          <Alert tone="error" title="Could not decode that">
            {error}
          </Alert>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          {/* how */}
          <div className="grid gap-3 sm:grid-cols-3">
            {MODES.map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => setMode(m.key)}
                aria-pressed={mode === m.key}
                className={`surface-lift rounded-2xl border p-4 text-left transition duration-200 ${
                  mode === m.key
                    ? "border-neon-500/50 bg-neon-500/10 shadow-glow"
                    : "border-line bg-surface-card hover:border-line-strong hover:bg-surface-hover"
                }`}
              >
                <span className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition ${
                      mode === m.key ? "border-neon-400" : "border-line-strong"
                    }`}
                  >
                    {mode === m.key && <span className="h-2 w-2 rounded-full bg-neon-400" />}
                  </span>
                  <span
                    className={`text-sm font-semibold ${
                      mode === m.key ? "text-neon-300" : "text-ink"
                    }`}
                  >
                    {m.label}
                  </span>
                </span>
                <span className="mt-2 block text-xs leading-relaxed text-muted">{m.blurb}</span>
              </button>
            ))}
          </div>

          <Card className="space-y-5 p-5">
            {mode === "upload" && (
              <Field
                label="Your refusal letter"
                hint="PDF, JPG, PNG or WebP. Include the page with the numbered boxes."
              >
                <label className="drop-zone flex cursor-pointer flex-col items-center justify-center px-6 py-10 text-center">
                  <input
                    type="file"
                    className="sr-only"
                    accept="application/pdf,image/jpeg,image/png,image/webp"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                  <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-neon-500/25 bg-neon-500/10 text-neon-400">
                    <FormIcon className="h-5 w-5" />
                  </span>
                  {file ? (
                    <>
                      <span className="mt-3.5 font-medium text-ink">{file.name}</span>
                      <span className="mt-1 text-xs text-muted">
                        {formatBytes(file.size)} · click to replace
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="mt-3.5 font-medium text-ink">Choose a file</span>
                      <span className="mt-1 text-xs text-muted">
                        A clear photo of the form is enough
                      </span>
                    </>
                  )}
                </label>
              </Field>
            )}

            {mode === "paste" && (
              <Field
                label="The wording of the refusal"
                hint="Paste as much as you have. The official phrasing is what we match on."
              >
                <Textarea
                  rows={10}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="e.g. Justification for the purpose and conditions of the intended stay was not provided…"
                />
              </Field>
            )}

            {mode === "pick" && grounds && (
              <div>
                <p className="mb-3 text-sm text-muted">
                  Select every box that is ticked on your letter. This is the most accurate
                  option, because you are reading the form yourself.
                </p>
                <ul className="space-y-2">
                  {grounds.map((g) => {
                    const on = picked.includes(g.code);
                    return (
                      <li key={g.code}>
                        <label
                          className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${
                            on
                              ? "border-neon-500/50 bg-neon-500/10"
                              : "border-line bg-surface-elevated hover:bg-surface-hover"
                          }`}
                        >
                          <input
                            type="checkbox"
                            className="mt-1 h-4 w-4 shrink-0 accent-[#3B82F6]"
                            checked={on}
                            onChange={() =>
                              setPicked((prev) =>
                                prev.includes(g.code)
                                  ? prev.filter((c) => c !== g.code)
                                  : [...prev, g.code],
                              )
                            }
                          />
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-ink">
                              <span className="text-muted">{g.number}. </span>
                              {g.plain}
                            </p>
                            <p className="mt-1 text-xs leading-relaxed text-muted">
                              {g.official}
                            </p>
                            {!g.fixable && (
                              <Badge className="mt-2 border-critical/30 bg-critical/10 text-critical">
                                Not fixable by reapplying
                              </Badge>
                            )}
                          </div>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            <Field
              label="Which application was this for?"
              hint="Optional, but it lets us tie each ground to that corridor's checklist."
            >
              <Select value={corridorId} onChange={(e) => setCorridorId(e.target.value)}>
                <option value="">Not sure / not listed</option>
                {corridors.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </Field>

            <Button onClick={submit} loading={busy} disabled={!ready} size="lg" className="w-full">
              Decode this refusal
            </Button>
          </Card>
        </div>

        <aside className="space-y-4">
          <Card>
            <CardHeader title="What you will get" />
            <ul className="space-y-3 p-5 text-sm leading-relaxed text-muted">
              <li>
                <strong className="text-ink">The grounds, in plain words.</strong> Which of
                the eleven were given, and what each actually means about your file.
              </li>
              <li>
                <strong className="text-ink">An honest verdict.</strong> Some grounds cannot
                be fixed with better paperwork. We will say so rather than sell you a
                re-check that cannot help.
              </li>
              <li>
                <strong className="text-ink">An ordered plan.</strong> What to change
                first, tied to the checklist for that corridor.
              </li>
              <li>
                <strong className="text-ink">A targeted re-check.</strong> Upload the
                rebuilt file and we will confirm, ground by ground, whether the things you
                were refused on are now clear.
              </li>
            </ul>
          </Card>

          <Card>
            <CardHeader title="Why the form is decodable" />
            <div className="p-5 pt-4">
            <p className="text-xs leading-relaxed text-muted">
              Annex VI of the EU Visa Code (Regulation 810/2009) fixes the refusal form and
              its eleven numbered grounds for all Schengen states. We match your letter
              against that official wording first and only fall back to AI if the text
              cannot be matched — so most letters are decoded exactly, not guessed at.
            </p>
            {source && (
              <a
                href={source}
                target="_blank"
                rel="noreferrer noopener"
                className="mt-3 inline-block text-xs font-medium text-neon-400 hover:underline"
              >
                Read the regulation →
              </a>
            )}
            </div>
          </Card>

          <Card className="border-warn/25">
            <CardHeader title="Important" />
            <p className="p-5 pt-4 text-xs leading-relaxed text-muted">
              This decodes what your letter says and maps it to document requirements. It is
              not legal advice, and it cannot tell you whether an appeal will succeed. Appeal
              deadlines are short and printed on your own letter — check that date before
              anything else.
            </p>
          </Card>
        </aside>
      </div>
      </div>
    </div>
  );
}

export default function DecodeRefusalPage() {
  return (
    <Suspense fallback={<Loading />}>
      <DecodeInner />
    </Suspense>
  );
}
