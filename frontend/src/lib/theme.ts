/**
 * Theme helpers.
 *
 * The theme is applied to `<html>` by a small inline script that runs before
 * the first paint (see `src/app/layout.tsx`), which is what prevents a flash
 * of the wrong theme.  These helpers mirror that script exactly so that the
 * client state and the DOM never disagree.
 */

export const THEME_STORAGE_KEY = "planet-health-theme";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

/** Read the persisted preference. */
export function readStoredTheme(): Theme {
  if (typeof window === "undefined") return "system";
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") {
      return stored;
    }
  } catch {
    // localStorage can be unavailable (private mode, blocked cookies).
  }
  return "system";
}

/** The operating system preference. */
export function systemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  } catch {
    return "light";
  }
}

/** Resolve a preference into the theme that is actually displayed. */
export function resolveTheme(theme: Theme): ResolvedTheme {
  return theme === "system" ? systemTheme() : theme;
}

/** Apply a preference to the document element. */
export function applyTheme(theme: Theme): ResolvedTheme {
  const resolved = resolveTheme(theme);

  if (typeof document !== "undefined") {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(resolved);
    root.style.colorScheme = resolved;
    root.dataset.theme = resolved;
    root.dataset.themePreference = theme;
  }

  return resolved;
}

/**
 * The inline script that runs before the first paint.
 *
 * It is rendered by the root layout (a Server Component), so it is part of
 * the server HTML and executes before React hydrates.
 */
export const THEME_INIT_SCRIPT = `(function(){try{
var k='${THEME_STORAGE_KEY}';
var t=localStorage.getItem(k)||'system';
if(t!=='light'&&t!=='dark'&&t!=='system'){t='system';}
var m=window.matchMedia('(prefers-color-scheme: dark)').matches;
var r=t==='system'?(m?'dark':'light'):t;
var d=document.documentElement;
d.classList.remove('light','dark');
d.classList.add(r);
d.style.colorScheme=r;
d.dataset.theme=r;
d.dataset.themePreference=t;
}catch(e){}})();`;
