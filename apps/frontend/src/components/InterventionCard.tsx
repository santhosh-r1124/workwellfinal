import { useState } from "react";

import { api } from "../api/client";
import type { Intervention } from "../types";
import Icon from "./Icon";

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
  // Seeded from the server: a suggestion the employee already rated has
  // closed the loop and must not re-prompt "how useful was this?" on every
  // reload. Local state after that, because a rating just given this session
  // need not round-trip before the thanks line shows.
  const [rated, setRated] = useState(intervention.has_feedback);
  const [failed, setFailed] = useState(false);

  // Both handlers used try/finally with no catch, so a failed request
  // simply re-enabled the buttons: the card looked as though the answer
  // had been recorded when nothing had been sent.
  const act = async (status: string) => {
    setBusy(true);
    setFailed(false);
    try {
      await api.respondToIntervention(intervention.id, status);
      onChange();
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const rate = async (rating: number) => {
    setBusy(true);
    setFailed(false);
    try {
      await api.submitInterventionFeedback(intervention.id, rating);
      setRated(true);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const answered = intervention.status !== "proposed";

  return (
    <article className="panel border-accent/25 bg-accent-ghost/40 p-4 mb-3 animate-fade-up">
      <div className="flex items-start justify-between gap-4 mb-2">
        <div className="flex items-center gap-2 text-accent">
          <Icon name="spark" className="w-3.5 h-3.5" />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.06em]">
            {TYPE_LABEL[intervention.type] || intervention.type}
          </span>
        </div>
        <time className="font-mono text-[11px] text-text-faint shrink-0">
          {intervention.created_at.slice(0, 10)}
        </time>
      </div>

      <p className="text-[13.5px] leading-relaxed mb-3">{intervention.message}</p>

      {!answered && (
        <div className="flex flex-wrap gap-2">
          <button disabled={busy} onClick={() => act("accepted")} className="btn-primary">
            That helps
          </button>
          <button disabled={busy} onClick={() => act("snoozed")} className="btn-quiet">
            Later
          </button>
          <button disabled={busy} onClick={() => act("dismissed")} className="btn-quiet">
            Not useful
          </button>
        </div>
      )}

      {failed && (
        <p role="alert" className="text-[12.5px] text-attention mt-2.5">
          That didn't go through. Nothing was recorded — try again.
        </p>
      )}

      {answered && !rated && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[12px] text-text-faint">
            Marked {intervention.status}. How useful was this?
          </span>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              disabled={busy}
              onClick={() => rate(n)}
              className="w-8 h-8 rounded-lg border border-line bg-surface-sunken font-mono text-[12px]
                         text-text-muted hover:text-text hover:bg-surface-raised disabled:opacity-50"
              aria-label={`Rate ${n} out of 5`}
            >
              {n}
            </button>
          ))}
        </div>
      )}

      {rated && (
        <p className="text-[12px] text-text-faint">Thanks — this tunes future suggestions.</p>
      )}
    </article>
  );
}
