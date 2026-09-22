import { useState } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import AssistantBubble from "./AssistantBubble";
import Icon from "./Icon";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  roles: string[];
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: "dashboard", roles: ["employee", "manager", "admin"] },
  { to: "/timeline", label: "Pattern timeline", icon: "timeline", roles: ["employee", "manager", "admin"] },
  { to: "/privacy", label: "Privacy centre", icon: "privacy", roles: ["employee", "manager", "admin"] },
  { to: "/teams", label: "Team analytics", icon: "teams", roles: ["manager", "admin"] },
  { to: "/admin", label: "Administration", icon: "admin", roles: ["admin"] },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const [navOpen, setNavOpen] = useState(false);

  if (!user) return <>{children}</>;

  const items = NAV.filter((i) => i.roles.includes(user.role));

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-[13.5px] transition-colors ${
      isActive
        ? "bg-accent-ghost text-accent font-medium"
        : "text-text-muted hover:text-text hover:bg-surface"
    }`;

  const sidebar = (
    <>
      <div className="flex items-center gap-2.5 px-3 pb-5">
        <span className="h-7 w-7 rounded-lg bg-gradient-to-br from-accent to-accent-deep" />
        <span className="font-bold tracking-tight">WorkWell AI</span>
      </div>

      <nav className="flex flex-col gap-1">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={linkClass}
            onClick={() => setNavOpen(false)}
          >
            <Icon name={item.icon} className="w-4 h-4 shrink-0" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto pt-6">
        <div className="rounded-lg border border-line-soft bg-surface-sunken px-3 py-2.5">
          <div className="text-[13px] font-medium truncate">{user.full_name}</div>
          <div className="text-[11px] text-text-faint capitalize">{user.role}</div>
          <button
            onClick={logout}
            className="mt-2.5 flex items-center gap-2 text-[12px] text-text-muted hover:text-text"
          >
            <Icon name="logout" className="w-3.5 h-3.5" />
            Log out
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex min-h-full">
      {/* Desktop rail */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-line-soft bg-ground px-3 py-5 sticky top-0 h-screen">
        {sidebar}
      </aside>

      {/* Mobile header + drawer */}
      <div className="md:hidden fixed inset-x-0 top-0 z-30 flex items-center justify-between border-b border-line-soft bg-ground/95 backdrop-blur px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-6 w-6 rounded-md bg-gradient-to-br from-accent to-accent-deep" />
          <span className="font-bold text-[15px]">WorkWell AI</span>
        </div>
        <button
          onClick={() => setNavOpen((v) => !v)}
          className="btn-quiet"
          aria-expanded={navOpen}
          aria-label="Toggle navigation"
        >
          {navOpen ? "Close" : "Menu"}
        </button>
      </div>

      {navOpen && (
        <div className="md:hidden fixed inset-0 z-20 bg-ground/98 flex flex-col px-3 pt-20 pb-6">
          {sidebar}
        </div>
      )}

      <main className="flex-1 min-w-0 pt-16 md:pt-0">
        {/* Extra bottom padding so the floating assistant never sits on top
            of the last element on the page. */}
        <div className="mx-auto w-full max-w-3xl px-4 md:px-8 pt-6 md:pt-10 pb-28">{children}</div>
      </main>

      <AssistantBubble />
    </div>
  );
}
