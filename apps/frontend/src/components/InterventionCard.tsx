import { useState } from "react";

import { api } from "../api/client";
import type { Intervention } from "../types";

const TYPE_LABEL: Record<string, string> = {
  focus_block: "Protected focus block",
  shutdown_reminder: "End-of-day boundary",
  recovery_break: "Recovery reminder",
  workplace_support_offer: "Workplace support",
  no_action: "No action",
};

export default function InterventionCard({
  intervention,
  onChange,
}: {
  intervention: Intervention;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [rated, setRated] = useState(false);

  const act = async (status: string) => {
    setBusy(true);
    try {
      await api.respondToIntervention(intervention.id, status);
      onChange();
    } finally {
      setBusy(false);
    }
  };

  const rate = async (rating: number) => {
    setBusy(true);
    try {
      await api.submitInterventionFeedback(intervention.id, rating);
      setRated(true);
    } finally {
      setBusy(false);
    }
  };

  const answered = intervention.status !== "proposed";

  return (
    <div className="rounded-lg border border-sky-900/60 bg-sky-950/30 p-4 mb-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-sky-400/80 mb-1">
            {TYPE_LABEL[intervention.type] || intervention.type}
          </div>
          <p className="text-sm text-slate-200">{intervention.message}</p>
        </div>
        <span className="text-xs text-slate-500 shrink-0">
          {intervention.created_at.slice(0, 10)}
        </span>
      </div>

      {!answered && (
        <div className="flex gap-2 mt-3">
          <button
            disabled={busy}
            onClick={() => act("accepted")}
            className="px-3 py-1.5 text-sm rounded-md bg-sky-500 hover:bg-sky-400 text-slate-950 font-medium disabled:opacity-50"
          >
            That helps
          </button>
          <button
            disabled={busy}
            onClick={() => act("snoozed")}
            className="px-3 py-1.5 text-sm rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 disabled:opacity-50"
          >
            Later
          </button>
          <button
            disabled={busy}
            onClick={() => act("dismissed")}
            className="px-3 py-1.5 text-sm rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
          >
            Not useful
          </button>
        </div>
      )}

      {answered && !rated && (
        <div className="flex items-center gap-2 mt-3">
          <span className="text-xs text-slate-500">
            Marked {intervention.status}. How useful was this, 1-5?
          </span>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              disabled={busy}
              onClick={() => rate(n)}
              className="w-7 h-7 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-50"
            >
              {n}
            </button>
          ))}
        </div>
      )}

      {rated && <p className="text-xs text-slate-500 mt-3">Thanks - this tunes future nudges.</p>}
    </div>
  );
}
