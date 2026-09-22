import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { SelfReportStatus } from "../types";

const SCALES: { key: "stress" | "energy" | "recovery"; label: string; hint: string }[] = [
  { key: "stress", label: "Stress", hint: "1 = calm, 5 = very stressed" },
  { key: "energy", label: "Energy", hint: "1 = depleted, 5 = energised" },
  { key: "recovery", label: "Recovery", hint: "1 = poor rest, 5 = well rested" },
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
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 mb-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-sm font-semibold text-slate-200">Daily check-in</h2>
        {status.submitted && !editing && (
          <button onClick={() => setEditing(true)} className="text-xs text-sky-400 hover:underline">
            Update
          </button>
        )}
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Your own words carry more weight than any signal we measure - this is what the system checks
        itself against.
      </p>

      {!showForm && (
        <p className="text-sm text-slate-300">
          Logged today · stress {status.stress} · energy {status.energy} · recovery{" "}
          {status.recovery}
        </p>
      )}

      {showForm && (
        <>
          {SCALES.map(({ key, label, hint }) => (
            <div key={key} className="mb-3">
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">{label}</span>
                <span className="text-slate-600 text-xs">{hint}</span>
              </div>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    onClick={() => setValues({ ...values, [key]: n })}
                    className={`w-9 h-9 rounded-md text-sm ${
                      values[key] === n
                        ? "bg-sky-500 text-slate-950 font-medium"
                        : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <button
            onClick={save}
            disabled={saving}
            className="mt-2 px-4 py-2 rounded-md bg-sky-500 hover:bg-sky-400 text-slate-950 font-medium text-sm disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save check-in"}
          </button>
        </>
      )}
    </div>
  );
}
