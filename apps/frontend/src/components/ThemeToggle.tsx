import { useTheme } from "../hooks/useTheme";
import Icon from "./Icon";

/** Two states, one control, and the label says what pressing it does
 *  rather than what is currently true - "Dark" on a light page reads as a
 *  status line, and people click it expecting to be told something. */
export default function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggle } = useTheme();
  const next = theme === "light" ? "dark" : "light";

  return (
    <button
      onClick={toggle}
      className={`group inline-flex items-center gap-2 rounded-xl px-2.5 py-1.5 text-[12px]
                  text-text-muted transition-colors hover:text-text ${className}`}
      style={{
        background: "var(--glass-bg)",
        border: "1px solid var(--glass-border)",
      }}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    >
      <Icon
        name={theme === "light" ? "moon" : "sun"}
        className="w-3.5 h-3.5 transition-transform group-hover:rotate-12"
      />
      <span className="capitalize">{next}</span>
    </button>
  );
}
