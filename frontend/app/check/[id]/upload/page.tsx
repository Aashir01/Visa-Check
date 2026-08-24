"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { FileIcon, SparkleIcon, UploadIcon } from "@/components/icons";
import { CHECK_STEPS, PageHeader } from "@/components/page-header";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Chip,
  EmptyState,
  Loading,
  Select,
  Spinner,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { formatBytes, titleCase } from "@/lib/format";
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
        setError("You have no checks remaining. Visit your account page to see your balance.");
      } else {
        setError(err instanceof Error ? err.message : "Could not start the analysis.");
      }
    }
  }

  if (authLoading || (!check && !error)) return <Loading />;

  return (
    <div>
      <PageHeader
        breadcrumbs={[
          { href: "/checks", label: "Your checks" },
          { href: "/check/new", label: "New check" },
          { label: "Upload" },
        ]}
        title="Upload your documents"
        lede="Drop the whole bundle in at once, in any order. We work out what each file is; you only need to correct us if we get one wrong."
        steps={CHECK_STEPS}
        currentStep={1}
        actions={
          check && (
            <div className="flex flex-wrap items-center gap-2">
              <Chip>{check.corridor_label}</Chip>
              {check.applicant_profile && <Chip>{titleCase(check.applicant_profile)}</Chip>}
            </div>
          )
        }
      />

      <div className="container-narrow py-8 lg:py-10">
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
          aria-label="Add documents"
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          className={`drop-zone cursor-pointer px-6 py-12 text-center ${dragging ? "drag-over" : ""}`}
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
            <div className="flex items-center justify-center gap-2.5 text-sm text-muted">
              <Spinner /> Uploading and encrypting…
            </div>
          ) : (
            <>
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-neon-500/25 bg-neon-500/10 text-neon-400">
                <UploadIcon className="h-6 w-6" />
              </span>
              <p className="mt-4 font-display text-lg font-semibold text-ink">
                Drop your documents here
              </p>
              <p className="mt-1 text-sm text-muted">or click to browse your files</p>
              <p className="mt-4 text-xs text-muted-soft">
                PDF, JPG, PNG or WebP · up to {MAX_MB} MB each
              </p>
            </>
          )}
        </div>

        {pending.length > 0 && (
          <div className="mt-4">
            <Alert tone="warning" title="Some files were not accepted">
              <ul className="mt-1.5 space-y-1">
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
        {docs.length > 0 ? (
          <Card className="mt-6">
            <CardHeader
              icon={<FileIcon className="h-4 w-4" />}
              title={`${docs.length} ${docs.length === 1 ? "document" : "documents"}`}
              subtitle="Types are detected when the check runs — override any that look wrong."
            />

            <ul className="divide-y divide-line">
              {docs.map((doc) => (
                <li key={doc.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-line bg-surface-elevated text-muted">
                    <FileIcon className="h-4 w-4" />
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{doc.filename}</p>
                    <p className="text-xs text-muted">
                      {formatBytes(doc.size_bytes)}
                      {doc.doc_type_label && doc.doc_type_source && (
                        <> · detected as {doc.doc_type_label}</>
                      )}
                    </p>
                  </div>

                  <div className="w-full sm:w-52">
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
                    <Badge className="border-neon-500/25 bg-neon-500/10 text-neon-300">
                      set by you
                    </Badge>
                  )}

                  <button
                    onClick={() => void removeDoc(doc.id)}
                    className="rounded-lg px-2.5 py-1.5 text-sm text-muted transition hover:bg-critical/10 hover:text-critical"
                    aria-label={`Remove ${doc.filename}`}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        ) : (
          <div className="mt-6">
            <EmptyState title="Nothing uploaded yet" icon={<FileIcon className="h-6 w-6" />}>
              Add your passport, financial evidence, bookings and letters. You can drop them all
              in one go and reorder nothing.
            </EmptyState>
          </div>
        )}

        {/* ---------------- run ---------------- */}
        <Card className="mt-8 p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="font-display text-base font-semibold text-ink">
                Ready when you are
              </h2>
              <p className="mt-1 text-sm text-muted">
                {docs.length === 0
                  ? "Upload at least one document to continue."
                  : "Analysis usually takes under a minute."}
              </p>
            </div>
            <Button
              onClick={runCheck}
              loading={running}
              disabled={docs.length === 0 || uploading}
              size="lg"
            >
              Analyse{" "}
              {docs.length > 0
                ? `${docs.length} document${docs.length === 1 ? "" : "s"}`
                : "documents"}
              <span aria-hidden>→</span>
            </Button>
          </div>

          {entitlement && (
            <div className="mt-5">
              <Alert tone={entitlement.ai_included ? "success" : "info"}>
                {entitlement.ai_included ? (
                  <>
                    <strong>Full check.</strong> Every checklist, identity, financial, date and
                    photo rule, plus the AI review of your letters.
                    {!entitlement.ai_always_included && (
                      <> You have {entitlement.ai_credits_remaining} full check(s) left.</>
                    )}
                  </>
                ) : (
                  <>
                    <strong>Free check.</strong> Every checklist, identity, financial, date and
                    photo rule runs. The AI review of your letters is not included.
                  </>
                )}
              </Alert>
            </div>
          )}

          <p className="mt-5 flex items-start gap-2 border-t border-line pt-4 text-xs leading-relaxed text-muted-soft">
            <SparkleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Your files are encrypted as soon as they arrive and deleted automatically after 30
            days. Running a check uses one credit; re-checking the same file afterwards does
            not.
          </p>
        </Card>
      </div>
    </div>
  );
}
