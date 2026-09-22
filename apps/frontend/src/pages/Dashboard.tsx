import { useEffect, useState } from "react";

import { api } from "../api/client";
import CheckIn from "../components/CheckIn";
import Explainability from "../components/Explainability";
import InterventionCard from "../components/InterventionCard";
import MetricBar from "../components/MetricBar";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import type { BaselineResponse, DailyHistoryPoint, Intervention, PatternRecord } from "../types";

// Matches shared/constants/wellbeing.py NEVER_COLLECTED_LABELS - a fixed
// product-wide constant, not per-employee data.
const NEVER_COLLECTED = ["Webcam", "Raw keyboard", "Message content", "Call recordings"];

const DIMENSIONS: {
  label: string;
  metric: string;
  unit: string;
  series: keyof DailyHistoryPoint;
}[] = [
  { label: "Schedule", metric: "work_duration", unit: "h", series: "work_duration" },
  { label: "Workload (meetings)", metric: "meeting_hours", unit: "h", series: "meeting_hours" },
  {
    label: "Recovery (avg. gap between breaks)",
    metric: "average_break_gap",
    unit: "m",
    series: "average_break_gap",
  },
  { label: "Focus", metric: "focus_minutes", unit: "m", series: "focus_minutes" },
  {
    label: "Communication (context switches)",
    metric: "context_switches",
    unit: "",
    series: "context_switches",
  },
];

const STATE_LABEL: Record<string, string> = {
  STABLE: "Stable",
  PATTERN_CHANGE: "Pattern change detected",
  SUSTAINED_STRAIN: "Sustained strain",
  SUPPORT_RECOMMENDED: "Support recommended",
  SAFETY_EVENT: "Safety event",
};

export default function Dashboard() {
  const { user } = useAuth();
  const [baseline, setBaseline] = useState<BaselineResponse | null>(null);
  const [patterns, setPatterns] = useState<PatternRecord[]>([]);
  const [interventions, setInterventions] = useState<Intervention[]>([]);
  const [history, setHistory] = useState<DailyHistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadInterventions = () => {
    api.listInterventions().then(setInterventions).catch(() => undefined);
  };

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    Promise.allSettled([
      api.getBaseline(user.id).then(setBaseline),
      api.getPatterns(user.id).then((res) => setPatterns(res.patterns)),
      api.getHistory(30).then((res) => setHistory(res.days)),
      api.listInterventions().then(setInterventions),
    ])
      .then((results) => {
        const failed = results.find((r) => r.status === "rejected");
        if (failed && failed.status === "rejected") setError(String(failed.reason));
      })
      .finally(() => setLoading(false));
  }, [user]);

  const latest = patterns[patterns.length - 1];
  const open = interventions.filter((i) => i.type !== "no_action");
  const changed = latest && latest.state !== "STABLE";

  const seriesFor = (key: keyof DailyHistoryPoint) =>
    history.map((d) => Number(d[key])).filter((n) => Number.isFinite(n));

  return (
    <>
      <PageHeader
        title="Today's work pattern"
        subtitle="Compared to your own history, not to anyone else's."
        status={
          latest && (
            <span
              className={`chip ${
                changed
                  ? "border-accent/40 bg-accent-ghost text-accent"
                  : "border-line text-text-muted"
              }`}
            >
              {STATE_LABEL[latest.state] || latest.state}
            </span>
          )
        }
      />

      {error && (
        <div className="panel border-attention/40 bg-attention-ghost px-4 py-3 mb-6 text-[13px] text-attention">
          Couldn't load part of your dashboard. {error}
        </div>
      )}

      {loading && (
        <div className="panel p-5 mb-6 space-y-3" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-3 rounded bg-surface-raised animate-pulse" style={{ width: `${90 - i * 18}%` }} />
          ))}
        </div>
      )}

      {changed && (
        <div className="panel-raised border-accent/25 bg-gradient-to-b from-accent-ghost to-transparent p-5 mb-6">
          <p className="text-[13.5px] text-[#bde5fb]">
            <strong className="font-semibold text-[#e6f6ff]">
              {STATE_LABEL[latest.state] || latest.state}.
            </strong>{" "}
            Your recent work pattern has differed from your usual pattern for {latest.duration_days}{" "}
            days (confidence {Math.round(latest.confidence * 100)}%). Ask the assistant why, any
            time.
          </p>
        </div>
      )}

      {open.length > 0 && (
        <section className="mb-7">
          <h2 className="eyebrow mb-2.5">Suggestions for you</h2>
          {open.slice(0, 3).map((intervention) => (
            <InterventionCard
              key={intervention.id}
              intervention={intervention}
              onChange={loadInterventions}
            />
          ))}
        </section>
      )}

      <CheckIn />

      <section className="mb-7">
        <h2 className="eyebrow mb-2.5">Signals</h2>
        <div className="panel px-5 py-4">
          {baseline &&
            DIMENSIONS.map((d) => {
              const m = baseline.metrics[d.metric];
              if (!m) return null;
              return (
                <MetricBar
                  key={d.metric}
                  label={d.label}
                  current={m.current}
                  baseline={m.baseline}
                  unit={d.unit}
                  history={seriesFor(d.series)}
                />
              );
            })}
          {!baseline && !loading && (
            <p className="text-text-muted text-[13px] py-2">
              Building your baseline — check back after a few days of activity.
            </p>
          )}
          {baseline && (
            <div className="flex justify-between pt-3 mt-1 font-mono text-[10px] text-text-faint">
              <span>0</span>
              <span>your norm</span>
              <span>2×</span>
            </div>
          )}
        </div>
      </section>

      <Explainability signals={latest?.signals || []} dataNotUsed={NEVER_COLLECTED} />
    </>
  );
}
