"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Loading,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { confidenceLabel, formatDateTime } from "@/lib/format";
import type { ReviewItem } from "@/lib/types";

export default function AdminReviewsPage() {
  const [status, setStatus] = useState("open");
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [types, setTypes] = useState<{ key: string; label: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    setItems(null);
    api.admin
      .reviews(status)
      .then(setItems)
      .catch((e: Error) => setError(e.message));
  }, [status]);

  useEffect(load, [load]);

  useEffect(() => {
    api.documentTypes().then(setTypes).catch(() => setTypes([]));
  }, []);

  return (
    <div className="container-page py-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-ink">Review queue</h1>
          <p className="mt-0.5 text-sm text-muted">
            Checks the pipeline was unsure about. Your corrections here are the accuracy
            feedback loop — they become evaluation data for the classifier.
          </p>
        </div>
        <div className="w-40">
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="all">All</option>
          </Select>
        </div>
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

      {!items && !error && <Loading />}

      {items?.length === 0 && (
        <EmptyState title="Nothing in the queue">
          Checks land here when a document could not be classified confidently, OCR quality
          was poor, or the overall confidence fell below the threshold.
        </EmptyState>
      )}

      <div className="space-y-4">
        {items?.map((item) => (
          <ReviewCard
            key={item.id}
            item={item}
            types={types}
            onResolved={(message) => {
              setNotice(message);
              load();
            }}
            onError={setError}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewCard({
  item,
  types,
  onResolved,
  onError,
}: {
  item: ReviewItem;
  types: { key: string; label: string }[];
  onResolved: (message: string) => void;
  onError: (message: string) => void;
}) {
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const documents = item.payload?.documents ?? [];
  const isOpen = item.status === "open";

  async function resolve(rerun: boolean) {
    setBusy(true);
    try {
      await api.admin.resolveReview(item.id, {
        correction: Object.keys(corrections).length
          ? { document_types: corrections }
          : undefined,
        notes: notes || undefined,
        rerun,
      });
      onResolved(
        rerun
          ? "Correction saved and the check was re-run."
          : "Correction saved.",
      );
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not resolve this item.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              className={
                isOpen
                  ? "border-warn/30 bg-amber-50 text-warn"
                  : "border-good/25 bg-emerald-50 text-good"
              }
            >
              {item.status}
            </Badge>
            {item.confidence != null && (
              <Badge className="border-line bg-gray-50 text-muted">
                confidence {item.confidence.toFixed(2)}
              </Badge>
            )}
            <span className="text-xs text-muted">{formatDateTime(item.created_at)}</span>
          </div>
          <p className="mt-2 text-sm text-ink">{item.reason}</p>
        </div>

        <Link
          href={`/check/${item.check_id}`}
          className="rounded-lg border border-line px-3 py-1.5 text-sm font-medium text-ink transition hover:bg-gray-50"
        >
          Open report
        </Link>
      </div>

      {documents.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                <th className="pb-2 font-medium">File</th>
                <th className="pb-2 font-medium">Detected as</th>
                <th className="pb-2 font-medium">Type conf.</th>
                <th className="pb-2 font-medium">OCR</th>
                {isOpen && <th className="pb-2 font-medium">Correct to</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {documents.map((doc) => {
                const typeConf = confidenceLabel(doc.type_confidence);
                const ocrConf = confidenceLabel(doc.ocr_confidence);
                return (
                  <tr key={doc.id}>
                    <td className="max-w-[220px] truncate py-2 pr-3 text-ink" title={doc.filename}>
                      {doc.filename}
                    </td>
                    <td className="py-2 pr-3 text-muted">{doc.detected_type ?? "unknown"}</td>
                    <td className={`py-2 pr-3 ${typeConf.tone}`}>
                      {doc.type_confidence?.toFixed(2) ?? "—"}
                    </td>
                    <td className={`py-2 pr-3 ${ocrConf.tone}`}>
                      {doc.ocr_confidence?.toFixed(2) ?? "—"}
                      <span className="ml-1 text-xs text-muted">{doc.ocr_engine}</span>
                    </td>
                    {isOpen && (
                      <td className="py-2">
                        <Select
                          value={corrections[doc.id] ?? ""}
                          onChange={(e) =>
                            setCorrections((c) => ({ ...c, [doc.id]: e.target.value }))
                          }
                          className="text-xs"
                          aria-label={`Correct type for ${doc.filename}`}
                        >
                          <option value="">Leave as detected</option>
                          {types.map((t) => (
                            <option key={t.key} value={t.key}>
                              {t.label}
                            </option>
                          ))}
                        </Select>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {isOpen ? (
        <div className="mt-4 border-t border-line pt-4">
          <Field label="Notes" hint="What was actually wrong? This is your training signal.">
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="text-sm"
            />
          </Field>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => void resolve(false)} disabled={busy}>
              {busy && <Spinner />} Save correction
            </Button>
            <Button onClick={() => void resolve(true)} disabled={busy}>
              Save and re-run check
            </Button>
          </div>
        </div>
      ) : (
        item.notes && (
          <p className="mt-3 border-t border-line pt-3 text-sm text-muted">
            <span className="font-medium text-ink">Notes: </span>
            {item.notes}
          </p>
        )
      )}
    </Card>
  );
}
