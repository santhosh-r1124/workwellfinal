import { useEffect, useState } from "react";

import { api } from "../api/client";
import ConnectorList from "../components/ConnectorList";
import DeviceList from "../components/DeviceList";
import PageHeader from "../components/PageHeader";
import Toggle from "../components/Toggle";
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
  const [notifications, setNotifications] = useState<boolean | null>(null);
  const [timezone, setTimezone] = useState<string | null>(null);

  const load = () => {
    api.getConsent().then(setSources);
  };

  useEffect(() => {
    load();
    api
      .getPreferences()
      .then((p) => {
        setNotifications(p.notifications_enabled);
        setTimezone(p.timezone);
      })
      .catch(() => setNotifications(null));
  }, []);

  const toggle = async (source: DataSourceInfo) => {
    // Org-disabled sources can still be turned *off* by the employee, but
    // there is nothing to turn off: the server already reports them off.
    if (!source.collectible || source.org_disabled) return;
    setBusy(source.key);
    try {
      await api.patchConsent(source.key, !source.enabled);
      load();
    } finally {
      setBusy(null);
    }
  };

  const toggleNotifications = async () => {
    if (notifications === null) return;
    const next = !notifications;
    setNotifications(next);
    try {
      await api.setNotifications(next);
    } catch {
      setNotifications(!next);
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
                <div className="flex items-center gap-2">
                  <span className="text-[13.5px] font-medium">{s.label}</span>
                  {s.org_disabled && (
                    <span className="chip border-attention/30 bg-attention/10 text-attention">
                      off org-wide
                    </span>
                  )}
                </div>
                <div className="text-[11.5px] text-text-faint capitalize">{s.category}</div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => setExpanded(expanded === s.key ? null : s.key)}
                  className="text-[12px] text-accent underline underline-offset-2 decoration-1 hover:decoration-2"
                  aria-expanded={expanded === s.key}
                >
                  {expanded === s.key ? "Hide" : "Details"}
                </button>
                <Toggle
                  checked={s.enabled}
                  onChange={() => toggle(s)}
                  label={s.label}
                  disabled={busy === s.key || s.org_disabled}
                />
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
                {s.org_disabled && (
                  <p className="pt-1 text-attention">
                    An administrator has switched this off for everyone in your organisation, so
                    nothing is being collected for it regardless of your own setting.
                  </p>
                )}
              </dl>
            )}
          </div>
        ))}
      </div>

      <DeviceList />

      <ConnectorList />

      {notifications !== null && (
        <>
          <h2 className="eyebrow mb-2.5">Notifications</h2>
          <div className="panel flex items-center justify-between gap-4 p-4 mb-3">
            <div className="min-w-0">
              <div className="text-[13.5px] font-medium">Email me when a suggestion is waiting</div>
              <p className="text-[11.5px] text-text-faint">
                The email says only that something is waiting — never what. Turning this off does
                not turn off support: suggestions still appear here.
              </p>
            </div>
            <Toggle
              checked={notifications}
              onChange={toggleNotifications}
              label="Email notifications"
            />
          </div>
          <p className="text-[12px] text-text-faint mb-2">
            This is a delivery preference, not consent. Consent is the list above, and withdrawing
            it stops collection entirely.
          </p>
          {timezone && (
            <p className="text-[12px] text-text-faint mb-8">
              Your day is measured in <span className="font-mono">{timezone}</span>, taken from your
              browser — everything here compares whole days, so that is where yours ends.
            </p>
          )}
        </>
      )}

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
