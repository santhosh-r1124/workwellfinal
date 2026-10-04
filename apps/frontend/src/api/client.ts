import type {
  AuditLogEntry,
  BaselineResponse,
  ChatMessage,
  DailyHistoryPoint,
  ConnectorInfo,
  DataSourceInfo,
  DegradedReason,
  DemoAccount,
  Device,
  DeviceCreated,
  Intervention,
  LiveStatus,
  OrgSettings,
  OrgUser,
  PatternRecord,
  Preferences,
  SelfReportPoint,
  SelfReportStatus,
  SupportResource,
  TeamAnalytics,
} from "../types";

import { demoHandler, isDemoActive } from "./demo";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("workwell_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Demo mode: answer from sample data, never touch the network. The real
  // request path below is used for every normal (non-demo) session.
  if (isDemoActive()) {
    const body = typeof options.body === "string" ? JSON.parse(options.body) : undefined;
    return demoHandler(path, options.method ?? "GET", body) as Promise<T>;
  }

  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user_id: string; role: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ id: string; email: string; full_name: string; role: string }>("/auth/me"),
  demoAccounts: () => request<DemoAccount[]>("/auth/demo-accounts"),
  getConsent: () => request<DataSourceInfo[]>("/consent"),
  setConsentBulk: (settings: Record<string, boolean>) =>
    request<DataSourceInfo[]>("/consent", { method: "POST", body: JSON.stringify(settings) }),
  patchConsent: (source: string, enabled: boolean) =>
    request<DataSourceInfo>(`/consent/${source}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  resetConsent: (source: string) => request<DataSourceInfo>(`/consent/${source}`, { method: "DELETE" }),
  getBaseline: (employeeId: string) => request<BaselineResponse>(`/employees/${employeeId}/baseline`),
  getPatterns: (employeeId: string) =>
    request<{ employee_id: string; patterns: PatternRecord[] }>(`/employees/${employeeId}/patterns`),
  chat: (message: string, sessionId: string | null) =>
    request<{
      session_id: string;
      reply: string;
      sources: ChatMessage["sources"];
      safety_flagged: boolean;
      degraded?: boolean;
      degraded_reason?: DegradedReason | null;
    }>("/chat", {
      method: "POST",
      body: JSON.stringify({ employee_id: "", session_id: sessionId, message }),
    }),
  ragQuery: (query: string, category?: string) =>
    request<{ answer: string; sources: { title: string; url?: string | null }[] }>("/rag/query", {
      method: "POST",
      body: JSON.stringify({ query, category }),
    }),

  getHistory: (days = 30) =>
    request<{ employee_id: string; days: DailyHistoryPoint[] }>(`/me/history?days=${days}`),
  listInterventions: () => request<Intervention[]>("/me/interventions"),
  respondToIntervention: (id: string, status: string, response?: string) =>
    request<Intervention>(`/me/interventions/${id}/respond`, {
      method: "POST",
      body: JSON.stringify({ status, response: response ?? null }),
    }),
  submitInterventionFeedback: (id: string, rating: number, comment?: string) =>
    request<{ id: string }>(`/me/interventions/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify({ rating, comment: comment ?? null }),
    }),
  liveStatus: () => request<LiveStatus>("/me/status"),
  listConnectors: () => request<{ connectors: ConnectorInfo[] }>("/me/connectors"),
  configureConnector: (key: string, config: Record<string, string>) =>
    request<{ connector: string; first_sync: { status: string; ingested_days: number } }>(
      `/me/connectors/${key}`,
      { method: "PUT", body: JSON.stringify({ config }) }
    ),
  syncConnector: (key: string) =>
    request<{ status: string; ingested_days: number }>(`/me/connectors/${key}/sync`, {
      method: "POST",
    }),
  disconnectConnector: (key: string) =>
    request<void>(`/me/connectors/${key}`, { method: "DELETE" }),

  listDevices: () => request<Device[]>("/me/devices"),
  createDevice: (label: string) =>
    request<DeviceCreated>("/me/devices", { method: "POST", body: JSON.stringify({ label }) }),
  revokeDevice: (id: string) => request<void>(`/me/devices/${id}`, { method: "DELETE" }),
  getPreferences: () => request<Preferences>("/me/preferences"),
  setNotifications: (enabled: boolean) =>
    request<Preferences>("/me/preferences", {
      method: "PATCH",
      body: JSON.stringify({ notifications_enabled: enabled }),
    }),
  setTimezone: (timezone: string) =>
    request<Preferences>("/me/preferences", {
      method: "PATCH",
      body: JSON.stringify({ timezone }),
    }),
  getTodaySelfReport: () => request<SelfReportStatus>("/me/self-report"),
  submitSelfReport: (stress: number, energy: number, recovery: number, note?: string) =>
    request<{ date: string }>("/me/self-report", {
      method: "POST",
      body: JSON.stringify({ stress, energy, recovery, note: note ?? null }),
    }),
  getSelfReportHistory: (days = 30) =>
    request<{ employee_id: string; reports: SelfReportPoint[] }>(
      `/me/self-report/history?days=${days}`
    ),
  getSupportResources: () =>
    request<{ resources: SupportResource[] }>("/me/support-resources"),

  listTeams: () => request<{ teams: string[] }>("/analytics/teams"),
  teamAnalytics: (team: string) =>
    request<TeamAnalytics>(`/analytics/teams/${encodeURIComponent(team)}`),

  getAdminSettings: () => request<OrgSettings>("/admin/settings"),
  updateAdminSettings: (patch: Partial<OrgSettings>) =>
    request<OrgSettings>("/admin/settings", { method: "PATCH", body: JSON.stringify(patch) }),
  getAdminDataSources: () =>
    request<{ data_sources: (DataSourceInfo & { never_collectible: boolean })[] }>(
      "/admin/data-sources"
    ),
  getAuditLogs: () => request<{ logs: AuditLogEntry[] }>("/admin/audit-logs"),
  getOrgUsers: () => request<{ users: OrgUser[] }>("/admin/users"),
  setUserActive: (userId: string, isActive: boolean) =>
    request<{ id: string; email: string; is_active: boolean }>(`/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),
  getIntegrations: () =>
    request<{
      connectors: {
        key: string;
        label: string;
        auth_kind: string;
        implemented: boolean;
        allowed: boolean;
      }[];
    }>("/admin/integrations"),
  applyRetention: () =>
    request<{ cutoff: string; daily_features_deleted: number; telemetry_events_deleted: number }>(
      "/admin/retention/apply",
      { method: "POST" }
    ),
  getAdminSupportResources: () =>
    request<{ categories: string[]; resources: SupportResource[] }>("/admin/support-resources"),
  createSupportResource: (body: {
    label: string;
    description?: string | null;
    category: string;
    url?: string | null;
    phone?: string | null;
    email?: string | null;
    sort_order?: number;
  }) =>
    request<SupportResource>("/admin/support-resources", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteSupportResource: (id: string) =>
    request<void>(`/admin/support-resources/${id}`, { method: "DELETE" }),
};

export { getToken };
