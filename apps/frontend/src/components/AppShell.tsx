import { useState } from "react";
import { NavLink } from "react-router-dom";

import { isDemoActive } from "../api/demo";
import { useAuth } from "../context/AuthContext";
import AssistantBubble from "./AssistantBubble";
import Icon from "./Icon";
import ThemeToggle from "./ThemeToggle";

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

/** The product mark. A lit glass chip rather than a flat square, so it
 *  belongs to the same material as everything else on the page. */
export function Mark({ size = 28 }: { size?: number }) {
  return (
    <span
      className="relative grid place-items-center rounded-xl shrink-0"
      style={{
        width: size,
        height: size,
        background: "linear-gradient(145deg, var(--accent), var(--accent-deep))",
        boxShadow: "0 6px 18px -8px rgb(var(--accent-rgb) / 0.85)",
      }}
    >
      <Icon name="spark" className="w-1/2 h-1/2 text-on-accent" />
      <span
        className="absolute inset-0 rounded-xl"
        style={{ background: "linear-gradient(to bottom, rgb(255 255 255 / 0.35), transparent 55%)" }}
        aria-hidden="true"
      />
    </span>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const [navOpen, setNavOpen] = useState(false);

  if (!user) return <>{children}</>;

  const items = NAV.filter((i) => i.roles.includes(user.role));

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `relative flex items-center gap-3 rounded-xl px-3 py-2 text-[13.5px] transition-all ${
      isActive
        ? "bg-accent-ghost text-accent font-medium shadow-[inset_0_1px_0_0_var(--glass-edge)]"
        : "text-text-muted hover:text-text hover:bg-[var(--glass-bg)]"
    }`;

  // The mobile drawer opens below a header that already shows the mark, so
  // it renders without one rather than stacking two identical logos.
  const sidebar = (withMark: boolean) => (
    <>
      {withMark && (
        <div className="flex items-center gap-2.5 px-3 pb-5">
          <Mark />
          <span className="font-bold tracking-tight">WorkWell AI</span>
        </div>
      )}

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

      <div className="mt-auto pt-6 space-y-2">
        <ThemeToggle className="w-full justify-center" />
        <div className="glass rounded-xl px-3 py-2.5">
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
      {/* Desktop rail. Translucent rather than solid: the ambient field
          behind the app runs under it, so the rail reads as a pane over
          the page instead of a separate dark column bolted to the side. */}
      <aside
        className="hidden md:flex w-60 shrink-0 flex-col px-3 py-5 sticky top-0 h-screen
                   border-r border-[var(--glass-border)] backdrop-blur-xl"
        style={{ background: "var(--glass-bg)" }}
      >
        {sidebar(true)}
      </aside>

      {/* Mobile header + drawer */}
      <div
        className="md:hidden fixed inset-x-0 top-0 z-30 flex items-center justify-between
                   border-b border-[var(--glass-border)] backdrop-blur-xl px-4 py-3"
        style={{ background: "var(--glass-bg-strong)" }}
      >
        <div className="flex items-center gap-2">
          <Mark size={24} />
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
        <div
          className="md:hidden fixed inset-0 z-20 flex flex-col px-3 pt-20 pb-6 backdrop-blur-2xl"
          style={{ background: "rgb(var(--ground-rgb) / 0.92)" }}
        >
          {sidebar(false)}
        </div>
      )}

      <main className="flex-1 min-w-0 pt-16 md:pt-0">
        {/* Extra bottom padding so the floating assistant never sits on top
            of the last element on the page. */}
        <div className="mx-auto w-full max-w-3xl px-4 md:px-8 pt-6 md:pt-10 pb-28">
          {isDemoActive() && (
            <div className="panel border-attention/40 bg-attention-ghost px-4 py-2.5 mb-6 text-[12.5px] text-attention">
              Demo mode — everything on screen is invented sample data, not a real analysis. Log out
              to leave demo mode.
            </div>
          )}
          {children}
        </div>
      </main>

      {/* Both are fixed, and the assistant sits above the drawer's layer -
          so with the drawer open it floated over the navigation, on top of
          the log-out card. It cannot go under the drawer either, because
          the drawer has to stay below the header that closes it. */}
      <div className={navOpen ? "hidden md:block" : undefined}>
        <AssistantBubble />
      </div>
    </div>
  );
}
