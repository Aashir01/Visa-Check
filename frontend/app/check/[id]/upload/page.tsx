"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  Field,
  Loading,
  Select,
  Spinner,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { formatBytes } from "@/lib/format";
import type { Check, DocumentOut, Entitlement } from "@/lib/types";

const ACCEPT = ".pdf,.jpg,.jpeg,.png,.webp";
const ACCEPTED_MIMES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/jpg",
  "image/png",
  "image/webp",
]);
const MAX_MB = 15;

interface Pending {
  name: string;
  size: number;
  error?: string;
}

export default function UploadPage() {
  const { user, loading: authLoading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const checkId = params.id;

  const [check, setCheck] = useState<Check | null>(null);
  const [docs, setDocs] = useState<DocumentOut[]>([]);
  const [types, setTypes] = useState<{ key: string; label: string }[]>([]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entitlement, setEntitlement] = useState<Entitlement | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.getCheck(checkId), api.documentTypes()])
      .then(([c, t]) => {
        setCheck(c);
        setDocs(c.documents);
        setTypes(t);
        if (c.status === "complete") router.replace(`/check/${checkId}`);
      })
      .catch((e: Error) => setError(e.message));

    api
      .account()
      .then((a) => setEntitlement(a.entitlement))
      .catch(() => setEntitlement(null));
  }, [user, checkId, router]);

  const addFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const incoming = Array.from(fileList);
      if (!incoming.length) return;

      const valid: File[] = [];
      const rejected: Pending[] = [];

      for (const f of incoming) {
        if (!ACCEPTED_MIMES.has(f.type)) {
          rejected.push({ name: f.name, size: f.size, error: "Unsupported file type" });
        } else if (f.size > MAX_MB * 1024 * 1024) {
          rejected.push({ name: f.name, size: f.size, error: `Larger than ${MAX_MB} MB` });
        } else if (f.size === 0) {
          rejected.push({ name: f.name, size: 0, error: "File is empty" });
        } else {
          valid.push(f);
        }
      }

      setPending(rejected);
      if (!valid.length) return;

      setError(null);
      setUploading(true);
      try {
        const created = await api.uploadDocuments(checkId, valid);
        setDocs((d) => [...d, ...created]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed.");
      } finally {
        setUploading(false);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [checkId],
  );

  async function removeDoc(documentId: string) {
    const previous = docs;
    setDocs((d) => d.filter((x) => x.id !== documentId));
    try {
      await api.deleteDocument(checkId, documentId);
    } catch (err) {
      setDocs(previous);
      setError(err instanceof Error ? err.message : "Could not remove the file.");
    }
  }

  async function setType(documentId: string, docType: string) {
    try {
      const updated = await api.setDocumentType(checkId, documentId, docType);
      setDocs((d) => d.map((x) => (x.id === documentId ? updated : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not set the document type.");
    }
  }

  async function runCheck() {
    setError(null);
    setRunning(true);
    try {
      await api.runCheck(checkId);
      router.push(`/check/${checkId}`);
    } catch (err) {
      setRunning(false);
      if (err instanceof ApiError && err.status === 402) {
        setError(
          "You have no checks remaining. Visit your account page to see your balance.",
        );
      } else {
        setError(err instanceof Error ? err.message : "Could not start the analysis.");
      }
    }
  }

  if (authLoading || (!check && !error)) return <Loading />;

  return (
    <div className="container-narrow py-10">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-ink">Upload your documents</h1>
        <p className="mt-1 text-muted">
          {check?.corridor_label}
          {check?.applicant_profile && ` · ${check.applicant_profile.replace(/_/g, " ")}`}
        </p>
      </div>

      {error && (
        <div className="mb-5">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {/* ---------------- dropzone ---------------- */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
          dragging
            ? "border-brand-600 bg-neon-500/10"
            : "border-line bg-white hover:border-neon-500/40/50"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => e.target.files && void addFiles(e.target.files)}
        />

        {uploading ? (
          <div className="flex items-center justify-center gap-2 text-sm text-muted">
            <Spinner /> Uploading and encrypting…
          </div>
        ) : (
          <>
            <svg viewBox="0 0 24 24" className="mx-auto h-8 w-8 fill-muted" aria-hidden>
              <path d="M12 3 7.5 7.5 9 9l2-2v8h2V7l2 2 1.5-1.5L12 3ZM4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2h-2v2H6v-2H4Z" />
            </svg>
            <p className="mt-3 font-medium text-ink">
              Drop your documents here, or click to browse
            </p>
            <p className="mt-1 text-sm text-muted">
              PDF, JPG, PNG or WebP · up to {MAX_MB} MB each
            </p>
          </>
        )}
      </div>

      {pending.length > 0 && (
        <div className="mt-4">
          <Alert tone="warning" title="Some files were not accepted">
            <ul className="mt-1 space-y-0.5">
              {pending.map((p) => (
                <li key={p.name}>
                  <span className="font-medium">{p.name}</span> — {p.error}
                </li>
              ))}
            </ul>
          </Alert>
        </div>
      )}

      {/* ---------------- uploaded files ---------------- */}
      {docs.length > 0 && (
        <Card className="mt-6">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <h2 className="font-semibold text-ink">
              {docs.length} {docs.length === 1 ? "document" : "documents"}
            </h2>
            <span className="text-xs text-muted">
              Types are detected when the check runs
            </span>
          </div>

          <ul className="divide-y divide-line">
            {docs.map((doc) => (
              <li key={doc.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink">{doc.filename}</p>
                  <p className="text-xs text-muted">
                    {formatBytes(doc.size_bytes)}
                    {doc.doc_type_label && doc.doc_type_source && (
                      <> · detected as {doc.doc_type_label}</>
                    )}
                  </p>
                </div>

                <div className="w-52">
                  <Select
                    value={doc.doc_type ?? ""}
                    onChange={(e) => void setType(doc.id, e.target.value)}
                    className="text-xs"
                    aria-label={`Document type for ${doc.filename}`}
                  >
                    <option value="">Detect automatically</option>
                    {types.map((t) => (
                      <option key={t.key} value={t.key}>
                        {t.label}
                      </option>
                    ))}
                  </Select>
                </div>

                {doc.doc_type_source === "user" && (
                  <Badge className="border-neon-500/25 bg-neon-500/10 text-neon-500">
                    set by you
                  </Badge>
                )}

                <button
                  onClick={() => void removeDoc(doc.id)}
                  className="rounded-lg px-2 py-1 text-sm text-muted transition hover:bg-critical/10 hover:text-critical"
                  aria-label={`Remove ${doc.filename}`}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* ---------------- run ---------------- */}
      <div className="mt-8 flex flex-col items-start gap-3">
        <Button
          onClick={runCheck}
          disabled={docs.length === 0 || running || uploading}
          size="lg"
        >
          {running && <Spinner />}
          Analyse {docs.length > 0 ? `${docs.length} document${docs.length === 1 ? "" : "s"}` : "documents"}
        </Button>

        {docs.length === 0 && (
          <p className="text-sm text-muted">Upload at least one document to continue.</p>
        )}

        {entitlement && (
          <div className="w-full max-w-xl">
            <Alert tone={entitlement.ai_included ? "success" : "info"}>
              {entitlement.ai_included ? (
                <>
                  <strong>Full check.</strong> Every checklist, identity, financial, date
                  and photo rule, plus the AI review of your letters.
                  {!entitlement.ai_always_included && (
                    <> You have {entitlement.ai_credits_remaining} full check(s) left.</>
                  )}
                </>
              ) : (
                <>
                  <strong>Free check.</strong> Every checklist, identity, financial, date
                  and photo rule runs. The AI review of your letters is not included.
                </>
              )}
            </Alert>
          </div>
        )}

        <p className="text-xs leading-relaxed text-muted">
          Your files are encrypted as soon as they arrive and deleted automatically after
          30 days. Analysis usually takes under a minute. Running a check uses one credit.
        </p>
      </div>
    </div>
  );
}
