import { useCallback, useEffect, useState } from "react";

import {
  type Theme,
  applyTheme,
  rememberTheme,
  storedTheme,
  systemTheme,
} from "../lib/theme";

/** Follows the operating system until the reader says otherwise, then stops.
 *
 *  Following the system forever would mean a reader who picked light at
 *  09:00 gets dropped back into dark when their laptop switches at dusk,
 *  having already told us what they wanted. An explicit choice is sticky;
 *  the absence of one is not.
 */
export function useTheme(): { theme: Theme; setTheme: (t: Theme) => void; toggle: () => void } {
  const [theme, setThemeState] = useState<Theme>(() => storedTheme() ?? systemTheme());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (storedTheme()) return;
    const query = window.matchMedia?.("(prefers-color-scheme: light)");
    if (!query) return;
    const onChange = () => setThemeState(systemTheme());
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const setTheme = useCallback((next: Theme) => {
    rememberTheme(next);
    setThemeState(next);
  }, []);

  const toggle = useCallback(
    () => setTheme(theme === "light" ? "dark" : "light"),
    [theme, setTheme]
  );

  return { theme, setTheme, toggle };
}
