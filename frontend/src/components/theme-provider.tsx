"use client";

import * as React from "react";

import {
  applyTheme,
  readStoredTheme,
  resolveTheme,
  THEME_STORAGE_KEY,
  type ResolvedTheme,
  type Theme,
} from "@/lib/theme";

type Listener = () => void;

const listeners = new Set<Listener>();

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function emit() {
  for (const listener of listeners) listener();
}

/**
 * `useSyncExternalStore` keeps the server render and the first client render
 * identical (the server snapshot is used during hydration) and then applies
 * the real preference, which avoids a hydration mismatch without a flash.
 */
function getClientTheme(): Theme {
  return readStoredTheme();
}

function getClientResolvedTheme(): ResolvedTheme {
  return resolveTheme(readStoredTheme());
}

function getServerTheme(): Theme {
  return "system";
}

function getServerResolvedTheme(): ResolvedTheme {
  return "light";
}

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);

export function ThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const theme = React.useSyncExternalStore(
    subscribe,
    getClientTheme,
    getServerTheme,
  );
  const resolvedTheme = React.useSyncExternalStore(
    subscribe,
    getClientResolvedTheme,
    getServerResolvedTheme,
  );

  const setTheme = React.useCallback((next: Theme) => {
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Ignore storage failures — the theme still applies for this page.
    }
    applyTheme(next);
    emit();
  }, []);

  // Keep the "system" option in step with the operating system preference.
  React.useEffect(() => {
    let media: MediaQueryList;
    try {
      media = window.matchMedia("(prefers-color-scheme: dark)");
    } catch {
      return;
    }

    const onChange = () => {
      if (readStoredTheme() === "system") {
        applyTheme("system");
        emit();
      }
    };

    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = React.useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used inside a <ThemeProvider>.");
  }
  return context;
}
