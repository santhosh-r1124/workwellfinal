import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const DEMO_ACCOUNTS = [
  { email: "employee.b@demo.workwell.ai", label: "Employee", hint: "rising overtime" },
  { email: "manager@demo.workwell.ai", label: "Manager", hint: "team aggregates" },
  { email: "admin@demo.workwell.ai", label: "Admin", hint: "org policy" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [password, setPassword] = useState("workwell-demo");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 mb-7">
          <span className="h-8 w-8 rounded-lg bg-gradient-to-br from-accent to-accent-deep" />
          <div>
            <div className="font-bold tracking-tight text-[17px] leading-tight">WorkWell AI</div>
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

        <div className="mt-5">
          <p className="eyebrow mb-2">Demo accounts</p>
          <div className="space-y-1.5">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.email}
                onClick={() => setEmail(a.email)}
                className={`w-full flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left transition-colors ${
                  email === a.email
                    ? "border-accent/40 bg-accent-ghost"
                    : "border-line-soft bg-surface hover:bg-surface-raised"
                }`}
              >
                <span className="text-[13px] font-medium">{a.label}</span>
                <span className="text-[11px] text-text-faint">{a.hint}</span>
              </button>
            ))}
          </div>
          <p className="text-[11.5px] text-text-faint mt-2.5">
            Password for all demo accounts: <span className="font-mono">workwell-demo</span>
          </p>
        </div>
      </div>
    </div>
  );
}
