import { useEffect, useState } from "react";

import { api } from "../api/client";
import CheckIn from "../components/CheckIn";
import Explainability from "../components/Explainability";
import InterventionCard from "../components/InterventionCard";
import MetricBar from "../components/MetricBar";
import { useAuth } from "../context/AuthContext";
import type { BaselineResponse, Intervention, PatternRecord } from "../types";

// Matches shared/constants/wellbeing.py NEVER_COLLECTED_LABELS - a fixed
// product-wide constant, not per-employee data.
const NEVER_COLLECTED = ["Webcam", "Raw keyboard", "Message content", "Call recordings"];

const DIMENSIONS: { label: string; metric: string; unit: string }[] = [
  { label: "Schedule", metric: "work_duration", unit: "h" },
  { label: "Workload (meetings)", metric: "meeting_hours", unit: "h" },
  { label: "Recovery (avg. gap between breaks)", metric: "average_break_gap", unit: "m" },
  { label: "Focus", metric: "focus_minutes", unit: "m" },
  { label: "Communication (context switches)", metric: "context_switches", unit: "" },
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
  const [error, setError] = useState<string | null>(null);

  const loadInterventions = () => {
    api.listInterventions().then(setInterventions).catch(() => undefined);
  };

  useEffect(() => {
    if (!user) return;
    api.getBaseline(user.id).then(setBaseline).catch((e) => setError(String(e)));
    api
      .getPatterns(user.id)
      .then((res) => setPatterns(res.patterns))
      .catch(() => undefined);
    loadInterventions();
  }, [user]);

  const latest = patterns[patterns.length - 1];

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-white mb-1">Today's Work Pattern</h1>
      <p className="text-sm text-slate-400 mb-6">Compared to your own history, not to anyone else's.</p>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      {latest && latest.state !== "STABLE" && (
        <div className="mb-6 rounded-lg border border-sky-800 bg-sky-950/40 p-4">
          <p className="text-sm text-sky-200">
            {STATE_LABEL[latest.state] || latest.state}: your recent work pattern has differed from
            your usual pattern for {latest.duration_days} days (confidence{" "}
            {Math.round(latest.confidence * 100)}%). See Pattern Timeline and the Assistant for
            details.
          </p>
        </div>
      )}

      {interventions.filter((i) => i.type !== "no_action").length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-semibold text-slate-200 mb-2">Suggestions for you</h2>
          {interventions
            .filter((i) => i.type !== "no_action")
            .slice(0, 3)
            .map((intervention) => (
              <InterventionCard
                key={intervention.id}
                intervention={intervention}
                onChange={loadInterventions}
              />
            ))}
        </div>
      )}

      <CheckIn />

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 mb-6">
        {baseline &&
          DIMENSIONS.map((d) => {
            const m = baseline.metrics[d.metric];
            if (!m) return null;
            return (
              <MetricBar key={d.metric} label={d.label} current={m.current} baseline={m.baseline} unit={d.unit} />
            );
          })}
        {!baseline && (
          <p className="text-slate-500 text-sm">
            Building your baseline - check back after a few days of activity.
          </p>
        )}
      </div>

      <Explainability signals={latest?.signals || []} dataNotUsed={NEVER_COLLECTED} />
    </div>
  );
}
