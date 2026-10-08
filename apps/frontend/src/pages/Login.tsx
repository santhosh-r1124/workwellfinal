import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Mark } from "../components/AppShell";
import ThemeToggle from "../components/ThemeToggle";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { DemoAccount } from "../types";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [directory, setDirectory] = useState<DemoAccount[]>([]);

  useEffect(() => {
    api
      .demoAccounts()
      .then((accounts) => setDirectory(accounts.filter((a) => a.role === "employee")))
      .catch(() => setDirectory([]));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError("Please enter email and password");
      return;
    }

    setBusy(true);
    try {
      await login(trimmedEmail, password);
      navigate("/");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(
        msg.startsWith("401")
          ? "Use one of the employee emails below. The password is the same as the email."
          : "Can't reach the WorkWell server. Make sure the backend is running on port 8000."
      );
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
          <div className="relative mb-4">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field w-full pr-10"
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-muted hover:text-text transition-colors"
              title={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? "👁️" : "👁️‍🗨️"}
            </button>
          </div>

          {error && (
            <p className="text-[13px] text-attention mb-3" role="alert">
              {error}
            </p>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full !py-2.5">
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {directory.length > 0 && (
          <div className="panel p-4 mt-4">
            <div className="text-[12px] font-semibold text-text-muted mb-0.5">Demo Employees</div>
            <div className="text-[11px] text-text-faint mb-2">Password is the same as the email.</div>
            <ul className="space-y-1">
              {directory.map((account) => (
                <li key={account.email}>
                  <button
                    type="button"
                    onClick={() => {
                      setEmail(account.email);
                      setPassword(account.email);
                      setError(null);
                    }}
                    className="w-full text-left px-2 py-1.5 rounded-md hover:bg-[var(--glass-bg)] transition-colors"
                  >
                    <div className="text-[13px] text-text">{account.email}</div>
                    {account.full_name && (
                      <div className="text-[11px] text-text-faint">{account.full_name}</div>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 text-center border-t border-slate-600 pt-6">
          <p className="text-slate-400 text-xs mb-2">Are you a manager, HR professional, or wellness consultant?</p>
          <Link
            to="/management"
            className="inline-block px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors text-sm"
          >
            Access Management Portal →
          </Link>
        </div>
      </div>
    </div>
  );
}
