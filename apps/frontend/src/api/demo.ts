/**
 * Frontend-only DEMO mode.
 *
 * This is a throwaway preview so the UI can be viewed with no backend running.
 * When demo mode is active, every API call is answered from the canned sample
 * data below instead of hitting the server. NONE of this is real: the numbers,
 * patterns and messages are invented purely so the screens render. It must
 * never be mistaken for a live analysis - the dashboard shows a banner saying
 * so while this is on.
 *
 * Turn it on by signing in with the demo credentials below; turn it off by
 * signing out. The real login path is untouched for any other credentials.
 */

export const DEMO_EMAIL = "demo@demomail.com";
export const DEMO_PASSWORD = "demopass";

const DEMO_FLAG = "workwell_demo";
const DEMO_TOKEN = "demo-token";

export function isDemoActive(): boolean {
  try {
    return localStorage.getItem(DEMO_FLAG) === "1";
  } catch {
    return false;
  }
}

export function enableDemo(): void {
  try {
    localStorage.setItem(DEMO_FLAG, "1");
    localStorage.setItem("workwell_token", DEMO_TOKEN);
  } catch {
    // Storage unavailable (private window); demo simply won't persist.
  }
}

export function disableDemo(): void {
  try {
    localStorage.removeItem(DEMO_FLAG);
  } catch {
    // ignore
  }
}

export function credentialsAreDemo(email: string, password: string): boolean {
  return email.trim().toLowerCase() === DEMO_EMAIL && password === DEMO_PASSWORD;
}

const DEMO_USER = {
  id: "demo-user",
  email: DEMO_EMAIL,
  full_name: "Demo User",
  role: "employee",
};

// --- mutable session state so interactions (respond / rate / check-in) stick
//     for as long as the tab is open ---------------------------------------

interface DemoIntervention {
  id: string;
  type: string;
  message: string;
  status: string;
  employee_response: string | null;
  created_at: string;
  has_feedback: boolean;
}

function daysAgoIso(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

function dateDaysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const interventions: DemoIntervention[] = [
  {
    id: "demo-int-1",
    type: "recovery_break",
    message:
      "Your evenings have run long for several days in a row. Protecting one proper break tomorrow may help you recover.",
    status: "proposed",
    employee_response: null,
    created_at: daysAgoIso(1),
    has_feedback: false,
  },
];

let todayReport: { stress: number; energy: number; recovery: number; note: string | null } | null =
  null;

const selfReports = [
  { date: dateDaysAgo(9), stress: 2, energy: 4, recovery: 4 },
  { date: dateDaysAgo(8), stress: 3, energy: 4, recovery: 3 },
  { date: dateDaysAgo(7), stress: 3, energy: 3, recovery: 3 },
  { date: dateDaysAgo(6), stress: 4, energy: 3, recovery: 2 },
  { date: dateDaysAgo(5), stress: 4, energy: 2, recovery: 2 },
  { date: dateDaysAgo(4), stress: 4, energy: 2, recovery: 2 },
  { date: dateDaysAgo(3), stress: 5, energy: 2, recovery: 1 },
  { date: dateDaysAgo(2), stress: 4, energy: 3, recovery: 2 },
];

function history() {
  const days = [];
  for (let i = 29; i >= 0; i--) {
    const strain = i < 8 ? (8 - i) / 8 : 0; // ramps up over the last ~week
    days.push({
      date: dateDaysAgo(i),
      work_duration: 7.5 + strain * 2.5 + Math.sin(i) * 0.3,
      after_hours: 0.3 + strain * 1.8,
      meeting_hours: 2.5 + Math.sin(i / 2) * 0.8,
      focus_minutes: 180 - strain * 70 + Math.cos(i) * 15,
      average_break_gap: 55 + strain * 40,
      context_switches: 40 + strain * 35 + Math.sin(i) * 5,
    });
  }
  return days;
}

function metric(current: number, baseline: number, unit_window = 14) {
  return {
    baseline,
    current,
    deviation: (current - baseline) / (baseline || 1),
    median: baseline,
    mean: baseline,
    std: baseline * 0.12,
    mad: baseline * 0.1,
    rolling_avg: current,
    trend: current - baseline,
    window_days: unit_window,
    metric: "",
  };
}

const baseline = {
  employee_id: DEMO_USER.id,
  readiness: { state: "ready", measured_days: 30, required_days: 7 },
  as_of: dateDaysAgo(1),
  metrics: {
    work_duration: metric(9.8, 7.6),
    meeting_hours: metric(3.1, 2.6),
    average_break_gap: metric(88, 56),
    focus_minutes: metric(120, 185),
    context_switches: metric(71, 42),
  },
};

const patterns = [
  {
    id: "demo-pat-1",
    date: dateDaysAgo(1),
    state: "PATTERN_CHANGE",
    confidence: 0.82,
    duration_days: 6,
    signals: [
      { name: "after_hours_work", change: 1.6, change_kind: "relative", anomalous_days: 6 },
      { name: "recovery_gap", change: 0.57, change_kind: "relative", anomalous_days: 5 },
      { name: "focus_fragmentation", change: 0.35, change_kind: "relative", anomalous_days: 5 },
    ],
  },
];

// Sample resources. No real or fake contact details: these demo rows show
// the plain text "Company number" / "Company email" as placeholders. In a
// live deployment an admin types the organisation's actual number, email and
// portal URL in Administration -> Support resources, and those real values
// are what employees see.
const supportResources = [
  {
    id: "demo-res-1",
    label: "24/7 Crisis Support Line",
    description: "Free, confidential support any time, day or night.",
    category: "crisis",
    url: null,
    phone: "Company number",
    email: "Company email",
    sort_order: 0,
    is_active: true,
  },
  {
    id: "demo-res-2",
    label: "Employee Assistance Programme",
    description: "Up to six free counselling sessions, booked confidentially.",
    category: "counselling",
    url: null,
    phone: "Company number",
    email: "Company email",
    sort_order: 1,
    is_active: true,
  },
  {
    id: "demo-res-3",
    label: "Wellbeing benefits portal",
    description: "Gym, mindfulness app and flexible-hours information.",
    category: "benefits",
    url: null,
    phone: "Company number",
    email: "Company email",
    sort_order: 2,
    is_active: true,
  },
];

function ok<T>(value: T): Promise<T> {
  return Promise.resolve(value);
}

/**
 * Answer an API call from the sample data. `path` is everything after the
 * base URL (may include a query string); `method` and `body` come from the
 * fetch options.
 */
export function demoHandler(path: string, method = "GET", body?: unknown): Promise<unknown> {
  const p = path.split("?")[0];
  const m = method.toUpperCase();

  // Auth
  if (p === "/auth/login")
    return ok({ access_token: DEMO_TOKEN, user_id: DEMO_USER.id, role: DEMO_USER.role });
  if (p === "/auth/me") return ok(DEMO_USER);
  if (p === "/auth/demo-accounts") return ok([]);

  // Dashboard core
  if (p.endsWith("/baseline")) return ok(baseline);
  if (p.endsWith("/patterns")) return ok({ employee_id: DEMO_USER.id, patterns });
  if (p === "/me/history") return ok({ employee_id: DEMO_USER.id, days: history() });
  if (p === "/me/status")
    return ok({
      version: `demo-${interventions.filter((i) => i.status === "proposed").length}`,
      analysed_at: daysAgoIso(1),
      last_data_at: daysAgoIso(0),
      open_interventions: interventions.filter((i) => i.status === "proposed").length,
    });

  // Interventions + the follow-up loop (feature D)
  if (p === "/me/interventions") return ok(interventions);
  if (p.startsWith("/me/interventions/") && p.endsWith("/respond")) {
    const id = p.split("/")[3];
    const row = interventions.find((i) => i.id === id);
    if (row) {
      row.status = (body as { status?: string })?.status ?? "accepted";
      row.employee_response = (body as { response?: string })?.response ?? null;
    }
    return ok(row);
  }
  if (p.startsWith("/me/interventions/") && p.endsWith("/feedback")) {
    const id = p.split("/")[3];
    const row = interventions.find((i) => i.id === id);
    if (row) row.has_feedback = true;
    return ok({ id });
  }

  // Self-report + pulse trend (feature B)
  if (p === "/me/self-report" && m === "GET")
    return ok(todayReport ? { submitted: true, ...todayReport } : { submitted: false });
  if (p === "/me/self-report" && m === "POST") {
    const b = body as { stress: number; energy: number; recovery: number };
    todayReport = { stress: b.stress, energy: b.energy, recovery: b.recovery, note: null };
    const today = dateDaysAgo(0);
    const existing = selfReports.find((r) => r.date === today);
    if (existing) Object.assign(existing, b);
    else selfReports.push({ date: today, ...b });
    return ok({ date: today });
  }
  if (p === "/me/self-report/history")
    return ok({ employee_id: DEMO_USER.id, reports: selfReports });

  // Support resources (feature C)
  if (p === "/me/support-resources") return ok({ resources: supportResources });

  // Preferences / devices / connectors — enough to render those screens
  if (p === "/me/preferences") return ok({ notifications_enabled: true, timezone: "UTC" });
  if (p === "/me/devices") return ok([]);
  if (p === "/me/connectors") return ok({ connectors: [] });

  // Consent screen
  if (p === "/consent") return ok([]);

  // Chat — a canned, clearly-demo reply
  if (p === "/chat")
    return ok({
      session_id: "demo-session",
      reply:
        "This is demo mode, so I'm answering from sample data. Your recent evenings have run longer than your own usual pattern for about a week — the suggestion on your dashboard is about protecting recovery time.",
      sources: [],
      safety_flagged: false,
      degraded: true,
      degraded_reason: "not_configured",
    });
  if (p === "/rag/query")
    return ok({ answer: "Sample guidance (demo mode).", sources: [] });

  // Analytics / admin — safe empties so those pages don't error
  if (p === "/analytics/teams") return ok({ teams: [] });

  // Default: an empty-ish success so an unmocked call never throws.
  return ok({});
}
