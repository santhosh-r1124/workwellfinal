import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { Mark } from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import type { TeamAnalytics, WellnessOverview } from "../types";

const STATE_LABELS: Record<string, string> = {
  STABLE: "Stable",
  PATTERN_CHANGE: "Sustained change",
  EMERGING_CHANGE: "Emerging change",
  BASELINE_BUILDING: "Building baseline",
  INSUFFICIENT_DATA: "Building baseline",
};

// Higher is better for energy and recovery; lower is better for stress.
const HIGHER_IS_BETTER: Record<string, boolean> = { stress: false, energy: true, recovery: true };

function formatChange(pct: number): string {
  if (pct === 0) return "No change";
  return `${pct > 0 ? "+" : ""}${pct}%`;
}

function changeTone(metric: string, pct: number): string {
  if (pct === 0) return "text-slate-300";
  const improving = HIGHER_IS_BETTER[metric] ? pct > 0 : pct < 0;
  return improving ? "text-green-400" : "text-amber-300";
}

function weekLabel(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export default function ManagementConsultant() {
  const navigate = useNavigate();
  const { user, loading, logout } = useAuth();
  const [overview, setOverview] = useState<WellnessOverview | null>(null);
  const [teams, setTeams] = useState<TeamAnalytics[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    if (!user || (user.role !== "manager" && user.role !== "admin")) {
      navigate("/management");
      return;
    }
    api
      .wellnessOverview()
      .then(setOverview)
      .catch(() => setError("Wellness insights are unavailable right now."));
    api
      .listTeams()
      .then(({ teams: names }) => Promise.all(names.map((t) => api.teamAnalytics(t))))
      .then(setTeams)
      .catch(() => setTeams([]));
  }, [loading, user, navigate]);

  const signOut = () => {
    logout();
    navigate("/management");
  };

  const latest = overview?.trend.length ? overview.trend[overview.trend.length - 1] : null;
  const changed = (overview?.pattern_states.PATTERN_CHANGE ?? 0) + (overview?.pattern_states.EMERGING_CHANGE ?? 0);
  const stable = overview?.pattern_states.STABLE ?? 0;

  const insights: { title: string; detail: string; tone: "positive" | "watch" | "neutral" }[] = [];
  if (overview?.sufficient_cohort) {
    insights.push(
      changed === 0
        ? {
            title: "No sustained pattern changes",
            detail: `All ${overview.employees} people are working within their own usual patterns. Continue routine check-ins.`,
            tone: "positive",
          }
        : {
            title: `${changed} sustained pattern change${changed === 1 ? "" : "s"}`,
            detail: "Support suggestions have been offered privately to the people concerned. Consider a cohort-wide workload review.",
            tone: "watch",
          },
    );
    for (const [metric, m] of Object.entries(overview.metrics)) {
      if (Math.abs(m.change_pct) < 5) continue;
      const improving = HIGHER_IS_BETTER[metric] ? m.change_pct > 0 : m.change_pct < 0;
      insights.push({
        title: `${overview.labels[metric]} ${m.direction === "up" ? "up" : "down"} ${Math.abs(m.change_pct)}%`,
        detail: `Compared with the previous ${overview.window_days} days, across ${m.contributing_employees} people.`,
        tone: improving ? "positive" : "watch",
      });
    }
    for (const team of teams) {
      for (const [metric, m] of Object.entries(team.metrics)) {
        if (Math.abs(m.change_pct) < 10) continue;
        insights.push({
          title: `${team.labels[metric]} ${m.direction === "up" ? "up" : "down"} ${Math.abs(m.change_pct)}% in ${team.team}`,
          detail: `Team median compared with the previous ${team.window_days} days.`,
          tone: "neutral",
        });
      }
    }
  }

  const toneClass = {
    positive: "bg-green-900/30 text-green-200 border border-green-700",
    watch: "bg-yellow-900/30 text-yellow-200 border border-yellow-700",
    neutral: "bg-slate-800 text-slate-200 border border-slate-600",
  };

  return (
    <div className="min-h-screen bg-slate-900">
      <div className="bg-gradient-to-r from-purple-900 to-purple-800 border-b border-purple-700 p-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <Mark size={36} />
            <div>
              <h1 className="text-2xl font-bold text-white">Wellness Consultant Portal</h1>
              <p className="text-purple-200 text-sm">Organisation-wide wellbeing insights</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {user && <span className="text-purple-100 text-sm hidden sm:inline">{user.full_name}</span>}
            <button
              onClick={signOut}
              className="px-4 py-2 bg-purple-700 hover:bg-purple-600 text-white rounded transition-colors text-sm"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {error && <div className="p-4 rounded bg-red-900/30 border border-red-700 text-red-200 text-sm">{error}</div>}

        {!overview && !error && <div className="text-slate-400 text-sm">Loading wellbeing insights…</div>}

        {overview && !overview.sufficient_cohort && (
          <div className="p-6 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
            <div className="font-semibold text-white mb-1">Not enough people to show insights yet</div>
            <p className="text-sm">
              Wellbeing insights appear once at least {overview.min_cohort} people contribute check-ins, so no
              individual can be singled out. {overview.cohort_size} contributing so far.
            </p>
          </div>
        )}

        {overview && overview.sufficient_cohort && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: "People in programme", value: String(overview.employees), color: "from-blue-600 to-blue-700" },
                { label: "Working within usual pattern", value: String(stable), color: "from-green-600 to-green-700" },
                { label: "Sustained pattern changes", value: String(changed), color: "from-purple-600 to-purple-700" },
                {
                  label: "Check-in participation",
                  value: `${Math.round((overview.cohort_size / Math.max(overview.employees, 1)) * 100)}%`,
                  color: "from-amber-600 to-amber-700",
                },
              ].map((card) => (
                <div key={card.label} className={`rounded-lg p-5 bg-gradient-to-br ${card.color} text-white`}>
                  <div className="text-3xl font-bold">{card.value}</div>
                  <div className="text-sm opacity-90 mt-1">{card.label}</div>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-lg p-6">
                <h2 className="text-lg font-semibold text-white">Wellbeing check-ins</h2>
                <p className="text-slate-400 text-sm mb-5">
                  Cohort median, last {overview.window_days} days vs the {overview.window_days} before
                </p>
                <div className="space-y-5">
                  {Object.entries(overview.labels).map(([metric, label]) => {
                    const level = latest?.[metric as "stress" | "energy" | "recovery"] ?? null;
                    const m = overview.metrics[metric];
                    return (
                      <div key={metric}>
                        <div className="flex items-baseline justify-between mb-1.5">
                          <span className="text-slate-200 text-sm font-medium">{label}</span>
                          <span className="text-sm">
                            <span className="text-white font-semibold">
                              {level !== null ? `${level.toFixed(1)} / ${overview.scale_max}` : "—"}
                            </span>
                            {m && <span className={`ml-3 ${changeTone(metric, m.change_pct)}`}>{formatChange(m.change_pct)}</span>}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-700 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-purple-500"
                            style={{ width: `${level !== null ? (level / overview.scale_max) * 100 : 0}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {overview.trend.length > 0 && (
                  <div className="mt-6 overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-slate-400 text-left">
                          <th className="py-2 pr-4 font-medium">Week ending</th>
                          <th className="py-2 pr-4 font-medium">Stress</th>
                          <th className="py-2 pr-4 font-medium">Energy</th>
                          <th className="py-2 pr-4 font-medium">Recovery</th>
                          <th className="py-2 font-medium">People</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overview.trend.map((w) => (
                          <tr key={w.week_ending} className="border-t border-slate-700 text-slate-200">
                            <td className="py-2 pr-4">{weekLabel(w.week_ending)}</td>
                            <td className="py-2 pr-4">{w.stress ?? "—"}</td>
                            <td className="py-2 pr-4">{w.energy ?? "—"}</td>
                            <td className="py-2 pr-4">{w.recovery ?? "—"}</td>
                            <td className="py-2">{w.contributors}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Insights</h2>
                <div className="space-y-3">
                  {insights.map((insight) => (
                    <div key={insight.title} className={`p-3 rounded ${toneClass[insight.tone]}`}>
                      <div className="font-semibold text-sm">{insight.title}</div>
                      <div className="text-xs mt-1 opacity-90">{insight.detail}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {teams.map((team) => (
              <div key={team.team} className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                <h2 className="text-lg font-semibold text-white">Work patterns · {team.team}</h2>
                <p className="text-slate-400 text-sm mb-4">
                  Team median, last {team.window_days} days vs the {team.window_days} before · {team.cohort_size} people
                </p>
                {team.sufficient_cohort ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {Object.entries(team.labels).map(([metric, label]) => {
                      const m = team.metrics[metric];
                      return (
                        <div key={metric} className="rounded bg-slate-900/60 border border-slate-700 p-4">
                          <div className="text-slate-400 text-xs">{label}</div>
                          <div className="text-white text-xl font-semibold mt-1">
                            {m ? formatChange(m.change_pct) : "Not enough data"}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-slate-300 text-sm">Hidden until at least {team.min_cohort} people contribute.</p>
                )}
              </div>
            ))}

            <p className="text-slate-500 text-xs text-center">
              Aggregates only. Figures appear only when at least {overview.min_cohort} people contribute, so no
              individual can be identified.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
