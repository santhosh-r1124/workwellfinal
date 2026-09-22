import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { SelfReportStatus } from "../types";

const SCALES: { key: "stress" | "energy" | "recovery"; label: string; low: string; high: string }[] = [
  { key: "stress", label: "Stress", low: "calm", high: "very stressed" },
  { key: "energy", label: "Energy", low: "depleted", high: "energised" },
  { key: "recovery", label: "Recovery", low: "poor rest", high: "well rested" },
];

export default function CheckIn() {
  const [status, setStatus] = useState<SelfReportStatus | null>(null);
  const [values, setValues] = useState({ stress: 3, energy: 3, recovery: 3 });
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);

  const load = () => {
    api.getTodaySelfReport().then((res) => {
      setStatus(res);
      if (res.submitted) {
        setValues({
          stress: res.stress ?? 3,
          energy: res.energy ?? 3,
          recovery: res.recovery ?? 3,
        });
      }
    });
  };

  useEffect(load, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.submitSelfReport(values.stress, values.energy, values.recovery);
      setEditing(false);
      load();
    } finally {
      setSaving(false);
    }
  };

  if (!status) return null;
  const showForm = editing || !status.submitted;

  return (
    <section className="panel p-5 mb-7">
      <div className="flex items-center justify-between gap-3 mb-1">
        <h2 className="eyebrow">Daily check-in</h2>
        {status.submitted && !editing && (
          <button onClick={() => setEditing(true)} className="text-[12px] text-accent hover:underline">
            Update
          </button>
        )}
      </div>
      <p className="text-[12.5px] text-text-faint mb-4">
        Your own words carry more weight than any signal we measure — this is what the system checks
        itself against.
      </p>

      {!showForm && (
        <div className="flex flex-wrap gap-2">
          {SCALES.map((s) => (
            <span key={s.key} className="chip border-line text-text-muted">
              {s.label.toLowerCase()} {status[s.key]}
            </span>
          ))}
        </div>
      )}

      {showForm && (
        <>
          {SCALES.map(({ key, label, low, high }) => (
            <div key={key} className="mb-4 last:mb-0">
              <div className="flex justify-between items-baseline text-[13px] mb-1.5">
                <span className="font-medium">{label}</span>
                <span className="text-[11px] text-text-faint">
                  1 = {low} · 5 = {high}
                </span>
              </div>
              <div className="flex gap-1.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setValues({ ...values, [key]: n })}
                    aria-pressed={values[key] === n}
                    aria-label={`${label} ${n}`}
                    className={`h-9 flex-1 max-w-[52px] rounded-lg font-mono text-[13px] border transition-colors ${
                      values[key] === n
                        ? "bg-accent text-[#05131f] border-accent font-semibold"
                        : "bg-surface-sunken border-line text-text-muted hover:text-text hover:bg-surface-raised"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <button onClick={save} disabled={saving} className="btn-primary mt-4">
            {saving ? "Saving..." : "Save check-in"}
          </button>
        </>
      )}
    </section>
  );
}
