/** Light or dark, and where that choice is remembered.
 *
 *  The attribute is written to <html> by a tiny inline script in index.html
 *  before the bundle loads, not here: applying the theme in React means one
 *  frame of the wrong background, which on a dark-by-default product is a
 *  white flash in the reader's face on every navigation. This module owns
 *  the same rules so the two cannot drift - the key name and the fallback
 *  are defined once, here, and the boot script mirrors them.
 */
export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "workwell-theme";

/** Matches the inline boot script in index.html. */
export const PAINT: Record<Theme, string> = {
  dark: "#060b18",
  light: "#eff0f4",
};

export function storedTheme(): Theme | null {
  try {
    const value = localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    // Private mode, or storage disabled by policy. Not worth failing over.
    return null;
  }
}

export function systemTheme(): Theme {
  return typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);
  root.style.colorScheme = theme;
  root.style.background = PAINT[theme];

  // The browser chrome on mobile takes its colour from here; left alone it
  // stays dark navy behind a white page.
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", PAINT[theme]);
}

export function rememberTheme(theme: Theme): void {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Same as above: the choice just will not survive a reload.
  }
}
