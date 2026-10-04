import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api/client";
import { DEMO_EMAIL, DEMO_PASSWORD } from "../api/demo";
import { Mark } from "../components/AppShell";
import ThemeToggle from "../components/ThemeToggle";
import { useAuth } from "../context/AuthContext";
import type { DemoAccount } from "../types";

const ROLE_HINT: Record<string, string> = {
  employee: "their own pattern",
  manager: "team aggregates",
  admin: "org policy",
};

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Which fixture accounts this deployment still has - none, on anything
  // running on real data. Hardcoding them here meant the first screen of
  // the product kept offering credentials that had been purged, which
  // reads as a broken login rather than a cleaned database.
  const [demo, setDemo] = useState<DemoAccount[]>([]);
  useEffect(() => {
    api
      .demoAccounts()
      .then(setDemo)
      .catch(() => setDemo([]));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("That email and password didn't match an account.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-full flex items-center justify-center px-4 py-12">
      <div className="fixed top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm animate-fade-up">
        <div className="flex items-center gap-3 mb-7">
          <Mark size={34} />
          <div>
            <div className="font-bold tracking-tight text-[18px] leading-tight">WorkWell AI</div>
            <div className="text-[12px] text-text-faint leading-tight">
              Wellness early-warning &amp; support
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="panel-raised p-6">
          <label htmlFor="email" className="block text-[13px] text-text-muted mb-1.5">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="field mb-4"
            autoComplete="username"
          />

          <label htmlFor="password" className="block text-[13px] text-text-muted mb-1.5">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="field mb-4"
            autoComplete="current-password"
          />

          {error && (
            <p className="text-[13px] text-attention mb-3" role="alert">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full !py-2.5">
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {/* No-backend demo: these credentials switch the app to sample data
            so the UI can be explored with nothing running behind it. */}
        <button
          type="button"
          onClick={() => {
            setEmail(DEMO_EMAIL);
            setPassword(DEMO_PASSWORD);
          }}
          className="mt-4 w-full rounded-xl border border-[var(--glass-border)] bg-[var(--glass-bg)]
                     px-3 py-2.5 text-left hover:bg-[var(--glass-bg-strong)] transition-all"
        >
          <div className="text-[13px] font-medium">Try the demo (no backend needed)</div>
          <div className="text-[11.5px] text-text-faint font-mono mt-0.5">
            {DEMO_EMAIL} · {DEMO_PASSWORD}
          </div>
          <div className="text-[11px] text-text-faint mt-1">
            Fills the form — then press Sign in. Everything shown will be invented sample data.
          </div>
        </button>

        {demo.length > 0 && (
          <div className="mt-5">
            <p className="eyebrow mb-2">Demo accounts on this deployment</p>
            <div className="space-y-1.5">
              {demo.map((a) => (
                <button
                  key={a.email}
                  onClick={() => {
                    setEmail(a.email);
                    setPassword(a.password);
                  }}
                  className={`w-full flex items-center justify-between gap-3 rounded-xl border px-3 py-2 text-left transition-all ${
                    email === a.email
                      ? "border-accent/40 bg-accent-ghost"
                      : "border-[var(--glass-border)] bg-[var(--glass-bg)] hover:bg-[var(--glass-bg-strong)]"
                  }`}
                >
                  <span className="text-[13px] font-medium capitalize">{a.role}</span>
                  <span className="text-[11px] text-text-faint">
                    {ROLE_HINT[a.role] ?? a.email}
                  </span>
                </button>
              ))}
            </div>
            <p className="text-[11.5px] text-text-faint mt-2.5">
              Fixture accounts, seeded deliberately. They disappear from here once
              <span className="font-mono"> purge_demo_data.py </span>
              has run.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
