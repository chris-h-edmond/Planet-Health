"use client";

import * as React from "react";

import { modelsApi } from "@/lib/api";
import type { ModelStatus } from "@/lib/types";

interface ModelStatusState {
  status: ModelStatus | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

/**
 * Track the availability of the analysis models.
 *
 * The backend is the single source of truth — the UI never assumes that
 * inference is possible.
 */
export function useModelStatus(): ModelStatusState {
  const [status, setStatus] = React.useState<ModelStatus | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;

    (async () => {
      try {
        const next = await modelsApi.status();
        if (!active) return;
        setStatus(next);
        setError(null);
      } catch {
        if (!active) return;
        setError(
          "The model status could not be retrieved from the Planet Health API.",
        );
      } finally {
        if (active) setLoading(false);
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  const reload = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await modelsApi.status());
    } catch {
      setError(
        "The model status could not be retrieved from the Planet Health API.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  return { status, loading, error, reload };
}
