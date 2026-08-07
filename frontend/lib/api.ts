import type {
  Account,
  AdminUser,
  Check,
  CheckSummary,
  ChecklistPreview,
  Corridor,
  Costs,
  DocumentOut,
  Overview,
  Profile,
  ReviewItem,
  RulePack,
  RulePackSummary,
  User,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const TOKEN_KEY = "visaguard_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  details?: unknown;
  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/** Pull a readable message out of FastAPI's several error shapes. */
function readDetail(payload: unknown, fallback: string): string {
  if (typeof payload === "string") return payload;
  if (payload && typeof payload === "object") {
    const detail = (payload as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .filter(Boolean);
      if (parts.length) return parts.join("; ");
    }
    if (detail && typeof detail === "object" && "message" in detail) {
      return String((detail as { message: unknown }).message);
    }
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      "Could not reach the server. Check that the API is running.",
      0,
    );
  }

  if (res.status === 401 && typeof window !== "undefined") {
    setToken(null);
  }

  if (!res.ok) {
    let payload: unknown = null;
    try {
      payload = await res.json();
    } catch {
      /* body was not JSON */
    }
    const message = readDetail(payload, `Request failed (${res.status})`);
    throw new ApiError(message, res.status, payload);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // --- auth ---
  register: (body: {
    email: string;
    password: string;
    full_name?: string;
    organization_name?: string;
  }) =>
    request<{ access_token: string; user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  me: () => request<User>("/auth/me"),
  account: () => request<Account>("/auth/account"),

  // --- corridors ---
  corridors: () => request<Corridor[]>("/corridors"),
  checklist: (corridorId: string, profile: string) =>
    request<ChecklistPreview>(
      `/corridors/${corridorId}/checklist?profile=${encodeURIComponent(profile)}`,
    ),

  // --- checks ---
  documentTypes: () => request<{ key: string; label: string }[]>("/checks/document-types"),

  createCheck: (body: {
    corridor_id: string;
    applicant_profile: Profile;
    travel_from?: string | null;
    travel_to?: string | null;
  }) => request<Check>("/checks", { method: "POST", body: JSON.stringify(body) }),

  uploadDocuments: (checkId: string, files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<DocumentOut[]>(`/checks/${checkId}/documents`, {
      method: "POST",
      body: form,
    });
  },

  setDocumentType: (checkId: string, documentId: string, docType: string) =>
    request<DocumentOut>(`/checks/${checkId}/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify({ doc_type: docType }),
    }),

  deleteDocument: (checkId: string, documentId: string) =>
    request<void>(`/checks/${checkId}/documents/${documentId}`, { method: "DELETE" }),

  runCheck: (checkId: string) =>
    request<Check>(`/checks/${checkId}/run`, { method: "POST" }),

  getCheck: (checkId: string) => request<Check>(`/checks/${checkId}`),
  listChecks: () => request<CheckSummary[]>("/checks"),
  deleteCheck: (checkId: string) =>
    request<void>(`/checks/${checkId}`, { method: "DELETE" }),

  reportUrl: (checkId: string) => `${BASE}/checks/${checkId}/report.pdf`,

  /** PDF needs the bearer header, so fetch as a blob rather than linking. */
  downloadReport: async (checkId: string) => {
    const res = await fetch(`${BASE}/checks/${checkId}/report.pdf`, {
      headers: { Authorization: `Bearer ${getToken() ?? ""}` },
    });
    if (!res.ok) throw new ApiError("Could not download the report.", res.status);
    return res.blob();
  },

  // --- admin ---
  admin: {
    overview: (days = 7) => request<Overview>(`/admin/overview?days=${days}`),
    corridors: () => request<Corridor[]>("/admin/corridors"),
    updateCorridor: (id: string, body: { enabled?: boolean; label?: string; description?: string }) =>
      request<Corridor>(`/admin/corridors/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    rulepacks: (corridorId: string) =>
      request<RulePackSummary[]>(`/admin/corridors/${corridorId}/rulepacks`),
    rulepack: (id: string) => request<RulePack>(`/admin/rulepacks/${id}`),
    validateRulepack: (data: unknown) =>
      request<{ valid: boolean; errors: string[] }>("/admin/rulepacks/validate", {
        method: "POST",
        body: JSON.stringify({ data }),
      }),
    createRulepack: (
      corridorId: string,
      body: { version: string; data: unknown; notes?: string; unverified?: boolean; publish?: boolean },
    ) =>
      request<RulePack>(`/admin/corridors/${corridorId}/rulepacks`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    updateRulepack: (id: string, body: { data?: unknown; notes?: string; unverified?: boolean }) =>
      request<RulePack>(`/admin/rulepacks/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    publishRulepack: (id: string) =>
      request<RulePack>(`/admin/rulepacks/${id}/publish`, { method: "POST" }),
    rulepackAudit: (id: string) =>
      request<{ id: string; action: string; detail: unknown; user?: string; created_at: string }[]>(
        `/admin/rulepacks/${id}/audit`,
      ),

    reviews: (status = "open") => request<ReviewItem[]>(`/admin/reviews?status=${status}`),
    resolveReview: (
      id: string,
      body: { correction?: { document_types?: Record<string, string> }; notes?: string; rerun?: boolean },
    ) =>
      request<ReviewItem>(`/admin/reviews/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    users: (q?: string) =>
      request<AdminUser[]>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`),
    grantCredits: (id: string, credits: number) =>
      request<AdminUser>(`/admin/users/${id}/credits`, {
        method: "POST",
        body: JSON.stringify({ credits }),
      }),
    updateUser: (id: string, body: { role?: string; is_active?: boolean; plan?: string }) =>
      request<AdminUser>(`/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),

    costs: (days = 30) => request<Costs>(`/admin/costs?days=${days}`),
    purge: () =>
      request<{ checks_purged: number; files_removed: number }>("/admin/purge", {
        method: "POST",
      }),
  },
};
