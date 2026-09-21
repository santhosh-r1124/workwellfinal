import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { TeamAnalytics as TeamAnalyticsData } from "../types";

export default function TeamAnalytics() {
  const [teams, setTeams] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [data, setData] = useState<TeamAnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listTeams()
      .then((res) => {
        setTeams(res.teams);
        if (res.teams.length > 0) setSelected(res.teams[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selected) return;
    api.teamAnalytics(selected).then(setData).catch((e) => setError(String(e)));
  }, [selected]);

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-white mb-1">Team Analytics</h1>
      <p className="text-sm text-slate-400 mb-6">
        Aggregate trends only. Individual employees are never identified here, and a metric is
        withheld entirely unless enough people contributed data to both compared periods.
      </p>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {teams.length > 0 && (
        <div className="flex gap-2 mb-6 flex-wrap">
          {teams.map((team) => (
            <button
              key={team}
              onClick={() => setSelected(team)}
              className={`px-3 py-1.5 rounded-md text-sm ${
                selected === team
                  ? "bg-sky-500/20 text-sky-300"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {team}
            </button>
          ))}
        </div>
      )}

      {teams.length === 0 && !error && (
        <p className="text-slate-500 text-sm">No teams are configured for your organization yet.</p>
      )}

      {data && !data.sufficient_cohort && (
        <div className="rounded-lg border border-amber-800 bg-amber-950/30 p-4">
          <p className="text-sm text-amber-200">
            This team has {data.cohort_size} member{data.cohort_size === 1 ? "" : "s"} with data,
            below the minimum cohort size of {data.min_cohort}. Nothing is reported, because with a
            group this small an aggregate can effectively identify an individual.
          </p>
        </div>
      )}

      {data && data.sufficient_cohort && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
          <div className="flex justify-between text-xs text-slate-500 mb-4">
            <span>
              {data.team} · {data.cohort_size} people
            </span>
            <span>
              last {data.window_days} days vs. previous {data.window_days}
            </span>
          </div>

          {Object.entries(data.metrics).map(([metric, change]) => (
            <div key={metric} className="flex justify-between items-center py-2 border-b border-slate-800 last:border-0">
              <span className="text-sm text-slate-200">{data.labels[metric] || metric}</span>
              <span
                className={`text-sm font-medium ${
                  change.direction === "flat" ? "text-slate-400" : "text-sky-300"
                }`}
              >
                {change.direction === "up" ? "↑" : change.direction === "down" ? "↓" : "→"}{" "}
                {Math.abs(change.change_pct)}%
              </span>
            </div>
          ))}

          {Object.keys(data.metrics).length === 0 && (
            <p className="text-sm text-slate-500">
              No metric had enough contributors in both periods to report.
            </p>
          )}

          {data.suppressed.length > 0 && (
            <p className="text-xs text-slate-500 mt-4">
              Withheld for insufficient data:{" "}
              {data.suppressed.map((m) => data.labels[m] || m).join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
