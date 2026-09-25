import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { ConnectorInfo } from "../types";

const STATUS_COPY: Record<string, { label: string; tone: string }> = {
  ok: { label: "syncing", tone: "border-accent/30 bg-accent-ghost text-accent" },
  consent_off: { label: "consent off", tone: "border-attention/30 bg-attention/10 text-attention" },
  needs_reconnect: { label: "reconnect", tone: "border-attention/30 bg-attention/10 text-attention" },
  failed: { label: "not reachable", tone: "border-attention/30 bg-attention/10 text-attention" },
};

/** Sources the employee has connected themselves.
 *
 *  Deliberately on their screen rather than an administrator's: the
 *  credential is a private calendar URL, it belongs to them, and they
 *  must be able to remove it without asking anyone. */
export default function ConnectorList() {
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api
      .listConnectors()
      .then((r) => setConnectors(r.connectors))
      .catch(() => setConnectors([]));
  };

  useEffect(load, []);

  const save = async (connector: ConnectorInfo) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.configureConnector(connector.key, draft);
      const sync = result.first_sync;
      setMessage(
        sync.status === "ok"
          ? `Connected — pulled ${sync.ingested_days} day${sync.ingested_days === 1 ? "" : "s"}.`
          : sync.status === "consent_off"
            ? "Connected, but nothing will be collected until you turn that data source on above."
            : "Connected, but the first sync didn't work. Check the link and try again."
      );
      setEditing(null);
      setDraft({});
      load();
    } catch (err) {
      setError(
        String(err).includes("400")
          ? "That link doesn't look right, or it points somewhere this server won't fetch."
          : "Couldn't save that."
      );
    } finally {
      setBusy(false);
    }
  };

  const syncNow = async (connector: ConnectorInfo) => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.syncConnector(connector.key);
      setMessage(
        result.status === "ok"
          ? `Synced ${result.ingested_days} day${result.ingested_days === 1 ? "" : "s"}.`
          : `Sync reported: ${result.status.replace(/_/g, " ")}.`
      );
      load();
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async (connector: ConnectorInfo) => {
    setBusy(true);
    try {
      await api.disconnectConnector(connector.key);
      setMessage("Disconnected — the stored link has been deleted.");
      load();
    } finally {
      setBusy(false);
    }
  };

  const available = connectors.filter((c) => c.implemented);
  const needsSetup = connectors.filter((c) => !c.implemented);

  return (
    <>
      <h2 className="eyebrow mb-2.5">Connected sources</h2>

      <div className="space-y-2 mb-3">
        {available.map((c) => (
          <div key={c.key} className="panel overflow-hidden">
            <div className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[13.5px] font-medium">{c.label}</span>
                  {c.connected && c.last_sync_status && STATUS_COPY[c.last_sync_status] && (
                    <span className={`chip ${STATUS_COPY[c.last_sync_status].tone}`}>
                      {STATUS_COPY[c.last_sync_status].label}
                    </span>
                  )}
                </div>
                <div className="text-[11.5px] text-text-faint">
                  {c.connected ? c.config_hint || "connected" : c.notes}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {c.connected ? (
                  <>
                    <button
                      onClick={() => syncNow(c)}
                      disabled={busy}
                      className="btn-quiet !py-1 !px-2.5 text-[12px] disabled:opacity-50"
                    >
                      Sync now
                    </button>
                    <button
                      onClick={() => disconnect(c)}
                      disabled={busy}
                      className="btn-quiet !py-1 !px-2.5 text-[12px] disabled:opacity-50"
                    >
                      Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setEditing(editing === c.key ? null : c.key)}
                    className="btn-primary !py-1 !px-3 text-[12px]"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>

            {editing === c.key && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  save(c);
                }}
                className="border-t border-line-soft px-4 py-3.5 space-y-2 animate-fade-up"
              >
                {c.required_config.map((field) => (
                  <input
                    key={field}
                    value={draft[field] || ""}
                    onChange={(e) => setDraft({ ...draft, [field]: e.target.value })}
                    placeholder="https://calendar.google.com/calendar/ical/.../basic.ics"
                    aria-label={field.replace(/_/g, " ")}
                    className="field text-[13px] py-1.5 font-mono"
                  />
                ))}
                <p className="text-[11.5px] text-text-faint">
                  Your calendar's private subscribe link. Only start and end times are read —
                  titles, attendees and locations are discarded before anything is stored. The link
                  itself is encrypted and never shown again.
                </p>
                <button
                  type="submit"
                  disabled={busy || c.required_config.some((f) => !draft[f])}
                  className="btn-primary !py-1.5 !px-3 text-[13px]"
                >
                  Connect
                </button>
              </form>
            )}

            {c.connected && !c.consent_enabled && (
              <p className="border-t border-line-soft px-4 py-2.5 text-[11.5px] text-attention">
                Nothing is being collected from this: the matching data source above is switched
                off, and consent decides — not the connection.
              </p>
            )}
          </div>
        ))}
      </div>

      {message && <p className="text-[12px] text-accent mb-3">{message}</p>}
      {error && <p className="text-[12px] text-attention mb-3">{error}</p>}

      {needsSetup.length > 0 && (
        <p className="text-[12px] text-text-faint mb-8">
          {needsSetup.map((c) => c.label).join(", ")} need an OAuth app registered by an
          administrator, so they aren&apos;t offered here yet.
        </p>
      )}
    </>
  );
}
