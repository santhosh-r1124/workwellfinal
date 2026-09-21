import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { AuditLogEntry, OrgSettings } from "../types";

export default function Admin() {
  const [settings, setSettings] = useState<OrgSettings | null>(null);
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [sources, setSources] = useState<{ key: string; label: string; never_collectible: boolean }[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api.getAdminSettings().then(setSettings).catch((e) => setError(String(e)));
    api.getAuditLogs().then((r) => setLogs(r.logs)).catch(() => undefined);
    api.getAdminDataSources().then((r) => setSources(r.data_sources)).catch(() => undefined);
  };

  useEffect(load, []);

  const save = async (patch: Partial<OrgSettings>) => {
    setStatus(null);
    try {
      const updated = await api.updateAdminSettings(patch);
      setSettings(updated);
      setStatus("Saved.");
    } catch (e) {
      setError(String(e));
    }
  };

  const runRetention = async () => {
    setStatus(null);
    try {
      const result = await api.applyRetention();
      setStatus(
        `Retention applied (cutoff ${result.cutoff}): removed ${result.telemetry_events_deleted} telemetry events and ${result.daily_features_deleted} daily feature rows.`
      );
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-xl font-semibold text-white mb-1">Administration</h1>
      <p className="text-sm text-slate-400 mb-6">
        Organization-wide policy. Some guarantees are enforced in code and cannot be configured
        away.
      </p>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
      {status && <p className="text-sky-300 text-sm mb-4">{status}</p>}

      {settings && (
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 mb-6 space-y-4">
          <div>
            <label className="block text-sm text-slate-300 mb-1">Retention (days)</label>
            <input
              type="number"
              value={settings.retention_days}
              onChange={(e) => setSettings({ ...settings, retention_days: Number(e.target.value) })}
              onBlur={() => save({ retention_days: settings.retention_days })}
              className="w-32 px-3 py-2 rounded-md bg-slate-800 border border-slate-700 text-white"
            />
            <p className="text-xs text-slate-500 mt-1">
              Telemetry and daily features older than this are deleted when retention runs.
            </p>
          </div>

          <div>
            <label className="block text-sm text-slate-300 mb-1">Minimum cohort for team analytics</label>
            <input
              type="number"
              value={settings.aggregation_min_cohort}
              onChange={(e) =>
                setSettings({ ...settings, aggregation_min_cohort: Number(e.target.value) })
              }
              onBlur={() => save({ aggregation_min_cohort: settings.aggregation_min_cohort })}
              className="w-32 px-3 py-2 rounded-md bg-slate-800 border border-slate-700 text-white"
            />
            <p className="text-xs text-slate-500 mt-1">
              Can be raised, never lowered below the hard floor of 5.
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-300">Interventions enabled</div>
              <p className="text-xs text-slate-500">Turns off proactive nudges org-wide.</p>
            </div>
            <button
              onClick={() => save({ interventions_enabled: !settings.interventions_enabled })}
              className={`w-11 h-6 rounded-full transition-colors relative ${
                settings.interventions_enabled ? "bg-sky-500" : "bg-slate-700"
              }`}
            >
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                  settings.interventions_enabled ? "translate-x-5" : ""
                }`}
              />
            </button>
          </div>

          <button
            onClick={runRetention}
            className="px-4 py-2 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm"
          >
            Apply retention policy now
          </button>
        </div>
      )}

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 mb-6">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">Data sources</h2>
        <div className="space-y-1">
          {sources.map((s) => (
            <div key={s.key} className="flex justify-between text-sm">
              <span className="text-slate-300">{s.label}</span>
              <span className={s.never_collectible ? "text-slate-500" : "text-sky-300"}>
                {s.never_collectible ? "never collected" : "available"}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-lg p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">Recent audit log</h2>
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {logs.map((log) => (
            <div key={log.id} className="text-xs text-slate-400 flex gap-3">
              <span className="text-slate-600 shrink-0">{log.created_at.slice(0, 19)}</span>
              <span className="text-slate-300">{log.action}</span>
              <span className="text-slate-500 truncate">{log.resource}</span>
            </div>
          ))}
          {logs.length === 0 && <p className="text-sm text-slate-500">No audit entries yet.</p>}
        </div>
      </div>
    </div>
  );
}
