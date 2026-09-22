import { useEffect, useState } from "react";

import { api } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { AuditLogEntry, OrgSettings } from "../types";

interface Connector {
  key: string;
  label: string;
  auth_kind: string;
  implemented: boolean;
}

export default function Admin() {
  const [settings, setSettings] = useState<OrgSettings | null>(null);
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [sources, setSources] = useState<{ key: string; label: string; never_collectible: boolean }[]>([]);
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api.getAdminSettings().then(setSettings).catch((e) => setError(String(e)));
    api.getAuditLogs().then((r) => setLogs(r.logs)).catch(() => undefined);
    api.getAdminDataSources().then((r) => setSources(r.data_sources)).catch(() => undefined);
    api.getIntegrations().then((r) => setConnectors(r.connectors)).catch(() => undefined);
  };

  useEffect(load, []);

  const save = async (patch: Partial<OrgSettings>) => {
    setStatus(null);
    try {
      setSettings(await api.updateAdminSettings(patch));
      setStatus("Saved.");
    } catch (e) {
      setError(String(e));
    }
  };

  const runRetention = async () => {
    setStatus(null);
    try {
      const r = await api.applyRetention();
      setStatus(
        `Retention applied (cutoff ${r.cutoff}): removed ${r.telemetry_events_deleted} telemetry events and ${r.daily_features_deleted} daily feature rows.`
      );
      load();
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <>
      <PageHeader
        title="Administration"
        subtitle="Organisation-wide policy. Some guarantees are enforced in code and cannot be configured away."
      />

      {error && <p className="text-[13px] text-attention mb-4">{error}</p>}
      {status && <p className="text-[13px] text-accent mb-4">{status}</p>}

      {settings && (
        <section className="panel p-5 mb-7 space-y-5">
          <div>
            <label htmlFor="retention" className="block text-[13px] font-medium mb-1.5">
              Retention
            </label>
            <div className="flex items-center gap-2">
              <input
                id="retention"
                type="number"
                value={settings.retention_days}
                onChange={(e) => setSettings({ ...settings, retention_days: Number(e.target.value) })}
                onBlur={() => save({ retention_days: settings.retention_days })}
                className="field w-28 font-mono"
              />
              <span className="text-[12.5px] text-text-faint">days</span>
            </div>
            <p className="text-[11.5px] text-text-faint mt-1.5">
              Telemetry and daily features older than this are deleted when retention runs.
            </p>
          </div>

          <div>
            <label htmlFor="cohort" className="block text-[13px] font-medium mb-1.5">
              Minimum cohort for team analytics
            </label>
            <input
              id="cohort"
              type="number"
              value={settings.aggregation_min_cohort}
              onChange={(e) =>
                setSettings({ ...settings, aggregation_min_cohort: Number(e.target.value) })
              }
              onBlur={() => save({ aggregation_min_cohort: settings.aggregation_min_cohort })}
              className="field w-28 font-mono"
            />
            <p className="text-[11.5px] text-text-faint mt-1.5">
              Can be raised, never lowered below the hard floor of 5.
            </p>
          </div>

          <div className="flex items-center justify-between gap-4">
            <div>
              <div className="text-[13px] font-medium">Interventions enabled</div>
              <p className="text-[11.5px] text-text-faint">Turns off proactive nudges org-wide.</p>
            </div>
            <button
              onClick={() => save({ interventions_enabled: !settings.interventions_enabled })}
              role="switch"
              aria-checked={settings.interventions_enabled}
              aria-label="Interventions enabled"
              className={`relative h-6 w-11 shrink-0 rounded-full border transition-colors ${
                settings.interventions_enabled
                  ? "bg-accent-deep border-accent-deep"
                  : "bg-surface-raised border-line"
              }`}
            >
              <span
                className={`absolute top-[3px] left-[3px] h-4 w-4 rounded-full bg-white transition-transform ${
                  settings.interventions_enabled ? "translate-x-5" : ""
                }`}
              />
            </button>
          </div>

          <button onClick={runRetention} className="btn-quiet">
            Apply retention policy now
          </button>
        </section>
      )}

      <h2 className="eyebrow mb-2.5">Data sources</h2>
      <div className="panel overflow-hidden mb-7">
        {sources.map((s, i) => (
          <div
            key={s.key}
            className={`flex items-center justify-between gap-4 px-5 py-3 ${
              i < sources.length - 1 ? "border-b border-line-soft" : ""
            }`}
          >
            <span className="text-[13.5px]">{s.label}</span>
            <span
              className={`chip ${
                s.never_collectible
                  ? "border-line text-text-faint"
                  : "border-accent/30 bg-accent-ghost text-accent"
              }`}
            >
              {s.never_collectible ? "never collected" : "available"}
            </span>
          </div>
        ))}
      </div>

      <h2 className="eyebrow mb-2.5">Connectors</h2>
      <div className="panel overflow-hidden mb-7">
        {connectors.map((c, i) => (
          <div
            key={c.key}
            className={`flex items-center justify-between gap-4 px-5 py-3 ${
              i < connectors.length - 1 ? "border-b border-line-soft" : ""
            }`}
          >
            <div className="min-w-0">
              <div className="text-[13.5px]">{c.label}</div>
              <div className="text-[11.5px] text-text-faint">{c.auth_kind}</div>
            </div>
            <span
              className={`chip shrink-0 ${
                c.implemented
                  ? "border-accent/30 bg-accent-ghost text-accent"
                  : "border-line text-text-faint"
              }`}
            >
              {c.implemented ? "implemented" : "requires setup"}
            </span>
          </div>
        ))}
      </div>

      <h2 className="eyebrow mb-2.5">Recent audit log</h2>
      <div className="panel overflow-hidden max-h-96 overflow-y-auto">
        {logs.map((log, i) => (
          <div
            key={log.id}
            className={`flex items-center justify-between gap-4 px-5 py-2.5 ${
              i < logs.length - 1 ? "border-b border-line-soft" : ""
            }`}
          >
            <div className="min-w-0">
              <div className="text-[12.5px] font-mono truncate">{log.action}</div>
              <div className="text-[11px] text-text-faint truncate">{log.resource}</div>
            </div>
            <time className="font-mono text-[11px] text-text-faint shrink-0">
              {log.created_at.slice(0, 19).replace("T", " ")}
            </time>
          </div>
        ))}
        {logs.length === 0 && (
          <p className="px-5 py-6 text-center text-[13px] text-text-muted">No audit entries yet.</p>
        )}
      </div>
    </>
  );
}
