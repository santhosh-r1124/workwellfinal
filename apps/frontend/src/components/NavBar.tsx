import React from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm font-medium ${
    isActive ? "bg-sky-500/20 text-sky-300" : "text-slate-300 hover:text-white hover:bg-slate-800"
  }`;

export default function NavBar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <nav className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-10">
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-white">WorkWell AI</span>
        <div className="flex gap-1 ml-6">
          <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
          <NavLink to="/timeline" className={linkClass}>Pattern Timeline</NavLink>
          <NavLink to="/chat" className={linkClass}>Assistant</NavLink>
          <NavLink to="/privacy" className={linkClass}>Privacy Center</NavLink>
          {(user.role === "manager" || user.role === "admin") && (
            <NavLink to="/teams" className={linkClass}>Team Analytics</NavLink>
          )}
          {user.role === "admin" && (
            <NavLink to="/admin" className={linkClass}>Admin</NavLink>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3 text-sm text-slate-400">
        <span>{user.full_name}</span>
        <button onClick={logout} className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200">
          Log out
        </button>
      </div>
    </nav>
  );
}
