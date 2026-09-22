import { useEffect, useState } from "react";

import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
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

  const entries = data ? Object.entries(data.metrics) : [];
  const widest = Math.max(1, ...entries.map(([, c]) => Math.abs(c.change_pct)));

  return (
    <>
      <PageHeader
        title="Team analytics"
        subtitle="Aggregate trends only. Individuals are never identified, and a metric is withheld unless enough people contributed to both periods."
        status={
          data?.sufficient_cohort ? (
            <span className="chip border-line text-text-muted">{data.cohort_size} people</span>
          ) : undefined
        }
      />

      {error && <p className="text-[13px] text-attention mb-4">{error}</p>}

      {teams.length > 1 && (
        <div className="flex gap-2 flex-wrap mb-5">
          {teams.map((team) => (
            <button
              key={team}
              onClick={() => setSelected(team)}
              className={`btn ${
                selected === team ? "bg-accent-ghost text-accent" : "btn-quiet"
              }`}
            >
              {team}
            </button>
          ))}
        </div>
      )}

      {teams.length === 0 && !error && (
        <p className="text-[13px] text-text-muted">No teams are configured for your organisation yet.</p>
      )}

      {data && !data.sufficient_cohort && (
        <div className="panel border-attention/30 bg-attention-ghost p-5">
          <p className="text-[13.5px] text-attention">
            Withheld — this team has {data.cohort_size}{" "}
            {data.cohort_size === 1 ? "person" : "people"} with data, below the minimum cohort of{" "}
            {data.min_cohort}.
          </p>
          <p className="text-[12.5px] text-text-muted mt-2">
            With a group this small, an aggregate can effectively identify one person.
          </p>
        </div>
      )}

      {data && data.sufficient_cohort && (
        <>
          <div className="panel overflow-hidden">
            <div className="flex items-center justify-between gap-3 px-5 py-3 bg-surface-sunken border-b border-line-soft">
              <span className="text-[12px] text-text-faint">{data.team}</span>
              <span className="text-[12px] text-text-faint">
                last {data.window_days} days vs. previous {data.window_days}
              </span>
            </div>

            {entries.map(([metric, change], i) => {
              const up = change.change_pct >= 0;
              return (
                <div
                  key={metric}
                  className={`px-5 py-3.5 ${i < entries.length - 1 ? "border-b border-line-soft" : ""}`}
                >
                  <div className="flex items-center justify-between gap-4 mb-2">
                    <span className="text-[13.5px]">{data.labels[metric] || metric}</span>
                    <span
                      className={`font-mono text-[12.5px] tabular-nums shrink-0 ${
                        up ? "text-accent" : "text-positive"
                      }`}
                    >
                      {up ? "↑" : "↓"} {Math.abs(change.change_pct)}%
                    </span>
                  </div>
                  {/* Diverging from a centre line: direction is the point, so
                      the bar grows out from zero rather than from the left. */}
                  <div className="relative h-1.5 bg-surface-sunken rounded-full">
                    <span className="absolute left-1/2 -top-0.5 -bottom-0.5 w-px bg-line" />
                    <span
                      className={`absolute top-0 h-full rounded-full ${
                        up ? "bg-accent left-1/2" : "bg-positive right-1/2"
                      }`}
                      style={{ width: `${(Math.abs(change.change_pct) / widest) * 50}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {data.suppressed.length > 0 && (
            <p className="text-[12px] text-text-faint mt-3">
              Withheld for insufficient data:{" "}
              {data.suppressed.map((m) => data.labels[m] || m).join(", ")}
            </p>
          )}

          <p className="text-[12px] text-text-faint mt-4">
            An admin can raise the minimum cohort; the code clamps it so it can never go lower.
          </p>
        </>
      )}
    </>
  );
}
