import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { DataSourceInfo } from "../types";

export default function PrivacyCenter() {
  const [sources, setSources] = useState<DataSourceInfo[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = () => {
    api.getConsent().then(setSources);
  };

  useEffect(() => {
    load();
  }, []);

  const toggle = async (source: DataSourceInfo) => {
    if (!source.collectible) return;
    await api.patchConsent(source.key, !source.enabled);
    load();
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-white mb-1">Privacy Center</h1>
      <p className="text-sm text-slate-400 mb-6">
        Control exactly what WorkWell collects. Some signals are permanently disabled in this
        product, regardless of any toggle.
      </p>
      <div className="space-y-2">
        {sources.map((s) => (
          <div key={s.key} className="bg-slate-900 border border-slate-800 rounded-lg">
            <div className="flex items-center justify-between p-4">
              <div>
                <div className="text-sm font-medium text-white">{s.label}</div>
                <div className="text-xs text-slate-500">{s.collectible ? s.category : "Never collected"}</div>
              </div>
              <div className="flex items-center gap-3">
                <button className="text-xs text-sky-400 hover:underline" onClick={() => setExpanded(expanded === s.key ? null : s.key)}>
                  {expanded === s.key ? "Hide details" : "Details"}
                </button>
                <button
                  onClick={() => toggle(s)}
                  disabled={!s.collectible}
                  className={`w-11 h-6 rounded-full transition-colors relative ${
                    s.enabled ? "bg-sky-500" : "bg-slate-700"
                  } ${!s.collectible ? "opacity-40 cursor-not-allowed" : ""}`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                      s.enabled ? "translate-x-5" : ""
                    }`}
                  />
                </button>
              </div>
            </div>
            {expanded === s.key && (
              <div className="px-4 pb-4 text-xs text-slate-400 space-y-1 border-t border-slate-800 pt-3">
                <p>
                  <span className="text-slate-500">What is collected: </span>
                  {s.what}
                </p>
                <p>
                  <span className="text-slate-500">Why: </span>
                  {s.why}
                </p>
                <p>
                  <span className="text-slate-500">Where processed: </span>
                  {s.where}
                </p>
                <p>
                  <span className="text-slate-500">Retention: </span>
                  {s.retention}
                </p>
                <p>
                  <span className="text-slate-500">Who can access it: </span>
                  {s.who_can_access}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
