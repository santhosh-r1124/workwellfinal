import { useEffect, useState } from "react";

import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../context/AuthContext";
import { formatChange, signalLabel } from "../lib/formatSignal";
import type { PatternRecord } from "../types";

const STATE_LABEL: Record<string, string> = {
  STABLE: "Stable",
  PATTERN_CHANGE: "Pattern change detected",
  SUSTAINED_STRAIN: "Sustained strain",
  SUPPORT_RECOMMENDED: "Support recommended",
  SAFETY_EVENT: "Safety event",
};

export default function PatternTimeline() {
  const { user } = useAuth();
  const [patterns, setPatterns] = useState<PatternRecord[]>([]);

  useEffect(() => {
    if (!user) return;
    api.getPatterns(user.id).then((res) => setPatterns(res.patterns));
  }, [user]);

  const ordered = patterns.slice().reverse();

  return (
    <>
      <PageHeader
        title="Pattern timeline"
        subtitle="A single unusual day is normal variation. Five consecutive days is a pattern."
      />

      <div className="panel overflow-hidden">
        {ordered.map((p, i) => {
          const changed = p.state !== "STABLE";
          return (
            <div
              key={p.id ?? p.date}
              className={`flex gap-4 px-5 py-3.5 ${
                i < ordered.length - 1 ? "border-b border-line-soft" : ""
              }`}
            >
              <div className="flex flex-col items-center pt-1 shrink-0">
                <span
                  className={`h-2 w-2 rounded-full ${changed ? "bg-accent" : "bg-line"}`}
                  aria-hidden="true"
                />
                {i < ordered.length - 1 && <span className="w-px flex-1 bg-line-soft mt-1.5" />}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <span
                    className={`text-[13.5px] ${changed ? "text-accent font-medium" : "text-text-muted"}`}
                  >
                    {STATE_LABEL[p.state] || p.state}
                  </span>
                  <time className="font-mono text-[11.5px] text-text-faint">{p.date}</time>
                </div>
                {p.signals.length > 0 && (
                  <p className="text-[12px] text-text-faint mt-1">
                    {p.signals
                      .map((s) => `${signalLabel(s.name)} ${formatChange(s)}`)
                      .join(" · ")}
                  </p>
                )}
              </div>
            </div>
          );
        })}

        {patterns.length === 0 && (
          <p className="px-5 py-8 text-center text-[13px] text-text-muted">
            No pattern history yet — this fills in as your baseline builds.
          </p>
        )}
      </div>

      <p className="text-[12px] text-text-faint mt-4">
        The detector deliberately resists smooth, gradual drift: a robust median/MAD baseline adapts
        to it. What it looks for is a sustained shift that holds.
      </p>
    </>
  );
}
