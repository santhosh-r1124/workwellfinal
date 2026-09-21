import { useEffect, useState } from "react";

import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
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

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-white mb-4">Pattern Timeline</h1>
      <div className="space-y-3">
        {patterns
          .slice()
          .reverse()
          .map((p) => (
            <div key={p.date} className="flex items-start gap-4 bg-slate-900 border border-slate-800 rounded-lg p-4">
              <div className="text-sm text-slate-500 w-28 shrink-0">{p.date}</div>
              <div>
                <div className={`text-sm font-medium ${p.state === "STABLE" ? "text-slate-300" : "text-sky-300"}`}>
                  {STATE_LABEL[p.state] || p.state}
                </div>
                {p.signals.length > 0 && (
                  <div className="text-xs text-slate-500 mt-1">
                    {p.signals
                      .map(
                        (s) =>
                          `${s.name.replace(/_/g, " ")} ${s.change >= 0 ? "+" : ""}${Math.round(s.change * 100)}%`
                      )
                      .join(" · ")}
                  </div>
                )}
              </div>
            </div>
          ))}
        {patterns.length === 0 && <p className="text-slate-500 text-sm">No pattern history yet.</p>}
      </div>
    </div>
  );
}
