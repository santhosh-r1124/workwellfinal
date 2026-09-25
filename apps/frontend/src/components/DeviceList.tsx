import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { Device } from "../types";
import Icon from "./Icon";

function lastSeen(device: Device): string {
  if (!device.last_seen_at) return "has not reported yet";
  const seen = new Date(device.last_seen_at);
  const hours = (Date.now() - seen.getTime()) / 3_600_000;
  if (hours < 1) return "reporting now";
  if (hours < 24) return `last reported ${Math.floor(hours)}h ago`;
  return `last reported ${Math.floor(hours / 24)}d ago`;
}

/** Which machines are reporting about you, and the switch to cut one off.
 *  On the employee's own screen rather than an admin one, because that is
 *  a privacy control rather than an administrative detail. */
export default function DeviceList() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [label, setLabel] = useState("");
  const [issued, setIssued] = useState<{ label: string; token: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api.listDevices().then(setDevices).catch(() => setDevices([]));
  };

  useEffect(load, []);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.createDevice(label.trim());
      setIssued({ label: created.label, token: created.token });
      setLabel("");
      load();
    } catch (err) {
      setError(String(err).includes("400") ? "You have reached the device limit." : "Could not register that device.");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (device: Device) => {
    setBusy(true);
    try {
      await api.revokeDevice(device.id);
      load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h2 className="eyebrow mb-2.5">Your devices</h2>

      <div className="panel overflow-hidden mb-3">
        {devices.map((d, i) => (
          <div
            key={d.id}
            className={`flex items-center justify-between gap-4 px-4 py-3 ${
              i < devices.length - 1 ? "border-b border-line-soft" : ""
            }`}
          >
            <div className="min-w-0">
              <div className="text-[13.5px]">{d.label}</div>
              <div className="text-[11.5px] text-text-faint">{lastSeen(d)}</div>
            </div>
            <button
              onClick={() => revoke(d)}
              disabled={busy}
              className="btn-quiet !py-1 !px-2.5 text-[12px] disabled:opacity-50"
            >
              Revoke
            </button>
          </div>
        ))}
        {devices.length === 0 && (
          <p className="px-4 py-5 text-center text-[13px] text-text-muted">
            No devices are reporting about you.
          </p>
        )}
      </div>

      <form onSubmit={add} className="flex items-center gap-2 mb-3">
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Name a device, e.g. Work laptop"
          aria-label="Device name"
          className="field text-[13px] py-1.5"
          maxLength={80}
        />
        <button type="submit" disabled={busy || !label.trim()} className="btn-primary !py-1.5 !px-3 text-[13px]">
          Register
        </button>
      </form>

      {error && <p className="text-[12px] text-attention mb-3">{error}</p>}

      {issued && (
        <div className="panel p-4 mb-3 border-accent/30 bg-accent-ghost animate-fade-up">
          <div className="flex items-start justify-between gap-3 mb-2">
            <div className="text-[13px] font-medium">Token for “{issued.label}”</div>
            <button
              onClick={() => setIssued(null)}
              className="rounded-md p-1 text-text-faint hover:text-text"
              aria-label="Hide token"
            >
              <Icon name="close" />
            </button>
          </div>
          <code className="block break-all rounded-lg bg-surface-sunken border border-line px-3 py-2 font-mono text-[12px]">
            {issued.token}
          </code>
          <p className="mt-2 text-[11.5px] text-text-faint">
            Put this in the agent’s <span className="font-mono">WORKWELL_AGENT_TOKEN</span>. It is
            shown once and never stored — if you lose it, register another device and revoke this
            one.
          </p>
        </div>
      )}

      <p className="text-[12px] text-text-faint mb-8">
        Each token works for your account only: a device cannot report for anyone else, and
        revoking one stops that machine immediately.
      </p>
    </>
  );
}
