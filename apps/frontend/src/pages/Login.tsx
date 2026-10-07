import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Mark } from "../components/AppShell";
import ThemeToggle from "../components/ThemeToggle";
import { useAuth } from "../context/AuthContext";

// Registered trainee users
const REGISTERED_TRAINEES = [
  {
    email: "harish44443@gmail.com",
    name: "Harish Kumar",
    department: "Software Engineering",
  },
  {
    email: "karthikm6@gmail.com",
    name: "Karthik M",
    department: "Data Engineering",
  },
  {
    email: "sanika.g@gmail.com",
    name: "Sanika G",
    department: "AI/ML",
  },
  {
    email: "debothri.ghosh@gmail.com",
    name: "Debothri Ghosh",
    department: "Quality Engineering",
  },
  {
    email: "sksricharan2003@gmail.com",
    name: "S K Sricharan",
    department: "Cloud & DevOps",
  },
  {
    email: "Santhosh@gmail.com",
    name: "Santhosh Rajinikanth",
    department: "AI Engineering",
  },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);

    const trimmedEmail = email.trim();

    if (!trimmedEmail) {
      setError("Please enter an email");
      setBusy(false);
      return;
    }

    if (!password) {
      setError("Please enter a password");
      setBusy(false);
      return;
    }

    // Check if email is registered (password can be any character)
    const registeredUser = REGISTERED_TRAINEES.find(
      user => user.email.toLowerCase() === trimmedEmail.toLowerCase()
    );

    if (!registeredUser) {
      setError("Email not found");
      setBusy(false);
      return;
    }

    try {
      // Create session for trainee (no backend auth needed)
      localStorage.setItem("user_email", trimmedEmail);
      localStorage.setItem("user_name", registeredUser.name);
      localStorage.setItem("user_token", `trainee_${Date.now()}`);
      navigate("/");
    } catch {
      setError("Login failed. Please try again.");
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

        <div className="mt-6 text-center border-t border-slate-600 pt-6">
          <p className="text-slate-400 text-xs mb-2">Are you a manager, HR professional, or wellness consultant?</p>
          <a
            href="/management"
            className="inline-block px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded transition-colors text-sm"
          >
            Access Management Portal →
          </a>
        </div>
      </div>
    </div>
  );
}
