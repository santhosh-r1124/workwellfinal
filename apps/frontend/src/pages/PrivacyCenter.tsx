import { useEffect, useState } from "react";

import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { DataSourceInfo } from "../types";

const DISCLOSURE: { key: keyof DataSourceInfo; label: string }[] = [
  { key: "what", label: "What is collected" },
  { key: "why", label: "Why" },
  { key: "where", label: "Where processed" },
  { key: "retention", label: "Retention" },
  { key: "who_can_access", label: "Who can access it" },
];

export default function PrivacyCenter() {
  const [sources, setSources] = useState<DataSourceInfo[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    api.getConsent().then(setSources);
  };

  useEffect(load, []);

  const toggle = async (source: DataSourceInfo) => {
    if (!source.collectible) return;
    setBusy(source.key);
    try {
      await api.patchConsent(source.key, !source.enabled);
      load();
    } finally {
      setBusy(null);
    }
  };

  const collectible = sources.filter((s) => s.collectible);
  const never = sources.filter((s) => !s.collectible);

  return (
    <>
      <PageHeader
        title="Privacy centre"
        subtitle="Control exactly what WorkWell collects. Turning something off stops it being collected, not just hidden."
      />

      <div className="space-y-2 mb-8">
        {collectible.map((s) => (
          <div key={s.key} className="panel overflow-hidden">
            <div className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="text-[13.5px] font-medium">{s.label}</div>
                <div className="text-[11.5px] text-text-faint capitalize">{s.category}</div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => setExpanded(expanded === s.key ? null : s.key)}
                  className="text-[12px] text-accent hover:underline"
                  aria-expanded={expanded === s.key}
                >
                  {expanded === s.key ? "Hide" : "Details"}
                </button>
                <button
                  onClick={() => toggle(s)}
                  disabled={busy === s.key}
                  role="switch"
                  aria-checked={s.enabled}
                  aria-label={s.label}
                  className={`relative h-6 w-11 rounded-full border transition-colors disabled:opacity-50 ${
                    s.enabled ? "bg-accent-deep border-accent-deep" : "bg-surface-raised border-line"
                  }`}
                >
                  <span
                    className={`absolute top-[3px] left-[3px] h-4 w-4 rounded-full bg-white transition-transform ${
                      s.enabled ? "translate-x-5" : ""
                    }`}
                  />
                </button>
              </div>
            </div>

            {expanded === s.key && (
              <dl className="border-t border-line-soft px-4 py-3.5 space-y-1.5 text-[12px] animate-fade-up">
                {DISCLOSURE.map(({ key, label }) => (
                  <div key={key}>
                    <dt className="inline text-text-faint">{label}: </dt>
                    <dd className="inline text-text-muted">{String(s[key])}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        ))}
      </div>

      <h2 className="eyebrow mb-2.5">Never collected</h2>
      <div className="panel overflow-hidden mb-3">
        {never.map((s, i) => (
          <div
            key={s.key}
            className={`flex items-center justify-between gap-4 px-4 py-3 ${
              i < never.length - 1 ? "border-b border-line-soft" : ""
            }`}
          >
            <span className="text-[13.5px] text-text-muted">{s.label}</span>
            <span className="chip border-line text-text-faint">disabled in code</span>
          </div>
        ))}
      </div>
      <p className="text-[12px] text-text-faint">
        These four have no toggle because there is nothing to toggle: the consent API rejects any
        attempt to enable them, so the guarantee does not depend on this screen.
      </p>
    </>
  );
}
