import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("employee.b@demo.workwell.ai");
  const [password, setPassword] = useState("workwell-demo");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate("/");
    } catch {
      setError("Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-8 w-full max-w-sm">
        <h1 className="text-2xl font-semibold text-white mb-1">WorkWell AI</h1>
        <p className="text-sm text-slate-400 mb-6">Employee wellness early-warning &amp; support</p>

        <label className="block text-sm text-slate-300 mb-1">Email</label>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-4 px-3 py-2 rounded-md bg-slate-800 border border-slate-700 text-white"
        />

        <label className="block text-sm text-slate-300 mb-1">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-4 px-3 py-2 rounded-md bg-slate-800 border border-slate-700 text-white"
        />

        {error && <p className="text-sm text-red-400 mb-3">{error}</p>}

        <button
          type="submit"
          className="w-full py-2 rounded-md bg-sky-500 hover:bg-sky-400 text-slate-950 font-medium"
        >
          Sign in
        </button>

        <p className="text-xs text-slate-500 mt-4">
          Demo accounts: employee.a@demo.workwell.ai .. employee.e@demo.workwell.ai / workwell-demo
        </p>
      </form>
    </div>
  );
}
