import type {
  AuditLogEntry,
  BaselineResponse,
  ChatMessage,
  DailyHistoryPoint,
  DataSourceInfo,
  Intervention,
  OrgSettings,
  PatternRecord,
  SelfReportStatus,
  TeamAnalytics,
} from "../types";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("workwell_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
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
    request<{ session_id: string; reply: string; sources: ChatMessage["sources"]; safety_flagged: boolean }>(
      "/chat",
      { method: "POST", body: JSON.stringify({ employee_id: "", session_id: sessionId, message }) }
    ),
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
  getTodaySelfReport: () => request<SelfReportStatus>("/me/self-report"),
  submitSelfReport: (stress: number, energy: number, recovery: number, note?: string) =>
    request<{ date: string }>("/me/self-report", {
      method: "POST",
      body: JSON.stringify({ stress, energy, recovery, note: note ?? null }),
    }),

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
  getIntegrations: () =>
    request<{
      connectors: { key: string; label: string; auth_kind: string; implemented: boolean }[];
    }>("/admin/integrations"),
  applyRetention: () =>
    request<{ cutoff: string; daily_features_deleted: number; telemetry_events_deleted: number }>(
      "/admin/retention/apply",
      { method: "POST" }
    ),
};

export { getToken };
