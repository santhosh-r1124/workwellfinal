import React, { createContext, useContext, useEffect, useState } from "react";

import { api } from "../api/client";
import { credentialsAreDemo, disableDemo, enableDemo } from "../api/demo";

interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Where this person's day ends decides which day the dashboard compares
 *  and which days the analysis treats as finished. The browser already
 *  knows, so report it rather than making someone find their own zone in
 *  a list of six hundred. Silent on failure - it is a boundary
 *  preference, and UTC remains a workable default. */
function reportTimezone(): void {
  try {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (zone) void api.setTimezone(zone).catch(() => undefined);
  } catch {
    // Intl is unavailable; UTC it is.
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("workwell_token");
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((me) => {
        setUser(me);
        reportTimezone();
      })
      .catch(() => localStorage.removeItem("workwell_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    // Demo mode: the fixed demo credentials switch the whole app over to
    // sample data with no backend. Any other credentials take the real path.
    if (credentialsAreDemo(email, password)) {
      enableDemo();
    } else {
      disableDemo();
    }
    const res = await api.login(email, password);
    localStorage.setItem("workwell_token", res.access_token);
    const me = await api.me();
    setUser(me);
    reportTimezone();
  };

  const logout = () => {
    localStorage.removeItem("workwell_token");
    disableDemo();
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
