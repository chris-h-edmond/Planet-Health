"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ApiError, authApi, hasSessionHint } from "@/lib/api";
import type { User } from "@/lib/types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  refresh: () => Promise<User | null>;
  setUser: (user: User | null) => void;
  signOut: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = React.useState<User | null>(null);
  const [status, setStatus] = React.useState<AuthStatus>("loading");
  const router = useRouter();

  /**
   * Set to true as soon as the session is established. It stops a slower
   * session check from downgrading a state that a sign-in has already
   * improved.
   */
  const authenticatedRef = React.useRef(false);

  /**
   * Set (or clear) the current user.
   *
   * The status is kept in step with the user so that a successful sign-in
   * or registration immediately moves the application into the
   * "authenticated" state.
   */
  const setUser = React.useCallback((next: User | null) => {
    if (next) {
      authenticatedRef.current = true;
    }
    setUserState(next);
    setStatus(next ? "authenticated" : "unauthenticated");
  }, []);

  const refresh = React.useCallback(async () => {
    try {
      const current = await authApi.me();
      setUser(current);
      setStatus("authenticated");
      return current;
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) {
        setUser(null);
        setStatus("unauthenticated");
        return null;
      }
      // A network or server error should not be treated as "signed out".
      setStatus((current) => (current === "loading" ? "unauthenticated" : current));
      throw error;
    }
  }, [setUser]);

  React.useEffect(() => {
    let active = true;

    (async () => {
      // Without a session marker there is nothing to check — calling the API
      // would only produce a 401 for an anonymous visitor.  The state update
      // is deferred by one tick so that the effect body itself performs no
      // synchronous state update.
      if (!hasSessionHint()) {
        await Promise.resolve();
        if (!active || authenticatedRef.current) return;
        setUserState(null);
        setStatus("unauthenticated");
        return;
      }

      try {
        const current = await authApi.me();
        if (!active) return;
        setUser(current);
        setStatus("authenticated");
      } catch {
        if (!active || authenticatedRef.current) return;
        setUserState(null);
        setStatus("unauthenticated");
      }
    })();

    return () => {
      active = false;
    };
  }, [setUser]);

  const signOut = React.useCallback(async () => {
    try {
      await authApi.logout();
    } catch (error) {
      if (!(error instanceof ApiError && error.isUnauthorized)) {
        throw error;
      }
    } finally {
      authenticatedRef.current = false;
      setUserState(null);
      setStatus("unauthenticated");
      router.replace("/");
      router.refresh();
    }
  }, [router]);

  const value = React.useMemo<AuthContextValue>(
    () => ({ user, status, refresh, setUser, signOut }),
    [user, status, refresh, setUser, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an <AuthProvider>.");
  }
  return context;
}
