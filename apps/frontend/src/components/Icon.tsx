const PATHS: Record<string, string> = {
  dashboard: "M4 13h6V4H4v9Zm0 7h6v-5H4v5Zm9 0h7v-9h-7v9Zm0-16v5h7V4h-7Z",
  timeline: "M4 6h16M4 12h10M4 18h7",
  privacy: "M12 3l7 3v6c0 4.4-3 8.2-7 9-4-.8-7-4.6-7-9V6l7-3Z",
  teams: "M16 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm-8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 2c-2.7 0-6 1.3-6 4v2h12v-2c0-2.7-3.3-4-6-4Zm8 0c-.6 0-1.3.1-2 .2 1.2.9 2 2.1 2 3.8v2h6v-2c0-2.7-3.3-4-6-4Z",
  admin: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm7.4-2.6.9-.7-1.5-2.6-1.1.4a5.9 5.9 0 0 0-1.6-.9l-.2-1.2h-3l-.2 1.2c-.6.2-1.1.5-1.6.9l-1.1-.4-1.5 2.6.9.7a6 6 0 0 0 0 1.2l-.9.7 1.5 2.6 1.1-.4c.5.4 1 .7 1.6.9l.2 1.2h3l.2-1.2c.6-.2 1.1-.5 1.6-.9l1.1.4 1.5-2.6-.9-.7a6 6 0 0 0 0-1.2Z",
  chat: "M4 4h16v11H8l-4 4V4Z",
  close: "M6 6l12 12M18 6 6 18",
  send: "M3 11.5 21 3l-8.5 18-2-7-7-2.5Z",
  logout: "M10 4H5v16h5M15 8l4 4-4 4M19 12H9",
  spark: "M13 2 4 14h6l-1 8 9-12h-6l1-8Z",
};

const FILLED = new Set(["dashboard", "privacy", "teams", "admin", "chat", "send", "spark"]);

export default function Icon({
  name,
  className = "w-4 h-4",
}: {
  name: keyof typeof PATHS | string;
  className?: string;
}) {
  const d = PATHS[name] ?? PATHS.dashboard;
  const filled = FILLED.has(name);

  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
