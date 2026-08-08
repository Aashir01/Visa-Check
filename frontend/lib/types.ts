export type Severity = "critical" | "warning" | "info";
export type RiskBand = "low" | "moderate" | "elevated" | "high";
export type Profile = "employed" | "self_employed" | "student" | "retired";
export type CheckStatus = "draft" | "queued" | "processing" | "complete" | "failed";

export interface Org {
  id: string;
  name: string;
  plan: string;
  credits: number;
  brand_name?: string | null;
  brand_color?: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name?: string | null;
  role: "user" | "agency_admin" | "admin";
  credits: number;
  ai_credits: number;
  org?: Org | null;
}

export type AiStatus =
  | "included"
  | "not_in_tier"
  | "budget_exhausted"
  | "unavailable"
  | "not_applicable";

export interface Entitlement {
  tier: "free" | "paid" | "admin";
  plan: string;
  checks_remaining: number;
  ai_credits_remaining: number;
  ai_included: boolean;
  ai_always_included: boolean;
  reason: string;
}

export interface Corridor {
  id: string;
  key: string;
  label: string;
  origin_country: string;
  destination: string;
  visa_type: string;
  description?: string | null;
  enabled: boolean;
  rulepack_version?: string | null;
  rulepack_unverified: boolean;
  profiles: Record<string, string>;
}

export interface ChecklistDoc {
  key: string;
  label: string;
  why?: string;
  fix?: string;
  severity: Severity;
  alternatives: string[];
}

export interface ChecklistPreview {
  corridor: Corridor;
  profile: string;
  version: string;
  unverified: boolean;
  disclaimer: string;
  required_documents: ChecklistDoc[];
  optional_documents: ChecklistDoc[];
  key_thresholds: { label: string; value: string }[];
}

export interface Evidence {
  document_id?: string | null;
  document_type?: string | null;
  document_label?: string | null;
  filename?: string | null;
  field?: string | null;
  value?: unknown;
  currency?: string;
}

export type Authority = "law" | "member_state" | "official_guidance" | "heuristic";

export interface Issue {
  id: string;
  rule_id: string;
  authority?: Authority | null;
  sources?: string[];
  severity: Severity;
  category: string;
  title: string;
  detail: string;
  fix: string;
  evidence: Evidence[];
  documents: string[];
  confidence: number;
}

export interface DocumentOut {
  id: string;
  filename: string;
  mime: string;
  size_bytes: number;
  doc_type?: string | null;
  doc_type_label?: string | null;
  doc_type_confidence?: number | null;
  doc_type_source?: string | null;
  ocr_engine?: string | null;
  ocr_confidence?: number | null;
  page_count?: number | null;
  extracted?: { fields?: Record<string, unknown>; sources?: Record<string, string>; notes?: string[] } | null;
  image_metrics?: Record<string, number | string | boolean> | null;
}

export interface RuleOutcome {
  rule_id: string;
  title: string;
  category: string;
}

export interface Scoring {
  score: number;
  band: RiskBand;
  band_label: string;
  band_message: string;
  counts: Record<Severity, number>;
  penalty: number;
  penalty_by_severity: Record<Severity, number>;
}

export interface Extraction {
  scoring?: Scoring;
  passed?: RuleOutcome[];
  skipped?: RuleOutcome[];
  degraded_llm?: boolean;
  ai_status?: AiStatus;
  tier?: string;
  trip_days?: number | null;
  travel_start?: string | null;
  travel_end?: string | null;
  documents?: {
    id: string;
    type: string;
    label: string;
    filename: string;
    confidence: number;
    fields: Record<string, unknown>;
  }[];
}

export interface PackMeta {
  title?: string;
  version?: string;
  effective_date?: string;
  disclaimer?: string;
  unverified?: boolean;
  source_notes?: string[];
}

export interface Check {
  id: string;
  corridor_id: string;
  corridor_label?: string | null;
  applicant_profile: string;
  travel_from?: string | null;
  travel_to?: string | null;
  status: CheckStatus;
  error?: string | null;
  risk_score?: number | null;
  risk_band?: RiskBand | null;
  summary?: string | null;
  confidence?: number | null;
  issues?: Issue[] | null;
  extraction?: Extraction | null;
  rulepack_version?: string | null;
  rulepack_unverified: boolean;
  documents: DocumentOut[];
  documents_purged_at?: string | null;
  pack_meta?: PackMeta | null;
  created_at: string;
  completed_at?: string | null;
}

export interface CheckSummary {
  id: string;
  corridor_id: string;
  corridor_label?: string | null;
  applicant_profile: string;
  status: CheckStatus;
  risk_score?: number | null;
  risk_band?: RiskBand | null;
  document_count: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  rulepack_version?: string | null;
  created_at: string;
  completed_at?: string | null;
}

export interface RulePackSummary {
  id: string;
  corridor_id: string;
  version: string;
  status: "draft" | "published" | "archived";
  unverified: boolean;
  notes?: string | null;
  created_at: string;
  published_at?: string | null;
  is_active: boolean;
}

export interface RulePack extends RulePackSummary {
  data: Record<string, unknown>;
}

export interface ReviewItem {
  id: string;
  check_id: string;
  corridor_id: string;
  reason: string;
  confidence?: number | null;
  payload?: {
    documents?: {
      id: string;
      filename: string;
      detected_type?: string | null;
      type_confidence?: number | null;
      ocr_confidence?: number | null;
      ocr_engine?: string | null;
    }[];
  } | null;
  status: string;
  notes?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  credits: number;
  ai_credits: number;
  is_active: boolean;
  org_name?: string | null;
  check_count: number;
  created_at: string;
  last_login_at?: string | null;
}

export interface Overview {
  period_days: number;
  checks_today: number;
  checks_period: number;
  completed: number;
  failed: number;
  completion_rate?: number | null;
  llm_spend_usd: number;
  cost_per_check_usd?: number | null;
  avg_risk_score?: number | null;
  avg_duration_ms?: number | null;
  open_reviews: number;
  users: number;
  organizations: number;
  corridors_enabled: number;
  budget_per_check_usd: number;
  free_tier_ai_enabled: boolean;
  queue: {
    queued: number;
    processing: number;
    oldest_pending_seconds: number | null;
    worker_mode: string;
  };
}

export interface Costs {
  period_days: number;
  total_usd: number;
  checks_completed: number;
  cost_per_check_usd?: number | null;
  budget_per_check_usd: number;
  price_in_per_mtok: number;
  price_out_per_mtok: number;
  by_corridor: {
    corridor_id: string;
    corridor: string;
    checks: number;
    usd: number;
    usd_per_check?: number | null;
    tokens_in: number;
    tokens_out: number;
  }[];
  by_kind: { kind: string; calls: number; usd: number }[];
  most_expensive_checks: { check_id: string; corridor: string; usd: number; created_at: string }[];
}

export interface Account {
  user: User;
  plan: string;
  credits: number;
  org_credits: number;
  checks_run: number;
  org_checks_run: number;
  team_seats: number;
  retention_days: number;
  entitlement: Entitlement;
  daily_check_limit: number;
  checks_left_today: number;
}
