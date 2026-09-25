export interface MetricBaseline {
  metric: string;
  baseline: number;
  current: number;
  deviation: number;
  median: number;
  mean: number;
  std: number;
  mad: number;
  rolling_avg: number;
  trend: number;
  window_days: number;
}

export interface BaselineResponse {
  employee_id: string;
  metrics: Record<string, MetricBaseline>;
}

export interface PatternSignal {
  name: string;
  change: number;
  /** How to read `change`: a fraction of baseline, a multiple of the
   *  signal's typical variation, or a raw delta. */
  change_kind?: "relative" | "spread" | "absolute";
  anomalous_days: number;
}

export interface PatternRecord {
  id?: string;
  date: string;
  state: string;
  confidence: number;
  duration_days: number;
  signals: PatternSignal[];
}

export interface DataSourceInfo {
  key: string;
  label: string;
  category: string;
  what: string;
  why: string;
  where: string;
  retention: string;
  who_can_access: string;
  default_enabled: boolean;
  collectible: boolean;
  enabled: boolean;
  /**
   * Switched off org-wide by an administrator. Kept separate from
   * `collectible`: "WorkWell never collects this" and "your employer turned
   * this off" are different promises and must not read the same.
   */
  org_disabled: boolean;
}

export interface Preferences {
  notifications_enabled: boolean;
}

export interface Device {
  id: string;
  label: string;
  created_at: string;
  last_seen_at: string | null;
}

/** The plaintext token comes back exactly once, on creation. */
export interface DeviceCreated extends Device {
  token: string;
}

export interface OrgUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  team: string | null;
  is_active: boolean;
}

export interface ChatSource {
  title: string;
  url?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  /** The reply is a deterministic fallback, not model text. */
  degraded?: boolean;
}

export interface TeamMetricChange {
  change_pct: number;
  direction: "up" | "down" | "flat";
  contributing_employees: number;
}

export interface TeamAnalytics {
  team: string;
  window_days: number;
  as_of: string;
  labels: Record<string, string>;
  cohort_size: number;
  min_cohort: number;
  sufficient_cohort: boolean;
  metrics: Record<string, TeamMetricChange>;
  suppressed: string[];
}

export interface OrgSettings {
  org_id: string;
  retention_days: number;
  aggregation_min_cohort: number;
  interventions_enabled: boolean;
  model_name: string | null;
  disabled_sources: string[];
  allowed_integrations: string[];
}

export interface DailyHistoryPoint {
  date: string;
  work_duration: number;
  after_hours: number;
  meeting_hours: number;
  focus_minutes: number;
  average_break_gap: number;
  context_switches: number;
}

export interface Intervention {
  id: string;
  type: string;
  message: string;
  status: string;
  employee_response: string | null;
  created_at: string;
}

export interface SelfReportStatus {
  submitted: boolean;
  stress?: number;
  energy?: number;
  recovery?: number;
  note?: string | null;
}

export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  subject_user_id: string | null;
  action: string;
  resource: string;
  meta: Record<string, unknown>;
  created_at: string;
}
