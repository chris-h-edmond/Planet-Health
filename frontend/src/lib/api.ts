/**
 * Centralised API client.
 *
 * All browser traffic goes to the Next.js origin (`/api/...`), which proxies
 * the request to the FastAPI backend.  Keeping the API on the same origin as
 * the application avoids cross-domain cookie problems.
 *
 * Environment variables
 * ---------------------
 * NEXT_PUBLIC_API_URL   Base URL used by the browser (default: `/api`).
 * NEXT_PUBLIC_CSRF_COOKIE_NAME
 *                        Name of the readable cookie holding the CSRF token
 *                        (default: `ph_csrf`).
 */

import type {
  AnalysisDetail,
  ApiErrorBody,
  AuthResponse,
  DashboardStats,
  ModelStatus,
  PaginatedAnalyses,
  Prediction,
  User,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "/api";

const CSRF_COOKIE_NAME =
  process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "ph_csrf";

const SESSION_HINT_COOKIE_NAME =
  process.env.NEXT_PUBLIC_SESSION_HINT_COOKIE_NAME ?? "ph_session_hint";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isUnauthorized() {
    return this.status === 401;
  }

  get isModelUnavailable() {
    return this.status === 503;
  }
}

/** Read a cookie value from the document (browser only). */
export function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  if (!match) return null;
  try {
    return decodeURIComponent(match.slice(prefix.length));
  } catch {
    return match.slice(prefix.length);
  }
}

/**
 * Whether a session *may* exist in this browser.
 *
 * The marker cookie carries no authority — the HTTP-only session cookie
 * remains the only credential.  It simply avoids an unnecessary 401 round
 * trip for anonymous visitors.
 */
export function hasSessionHint(): boolean {
  return readCookie(SESSION_HINT_COOKIE_NAME) === "1";
}

/** Forget the session marker (used when the API reports the session is gone). */
export function clearSessionHint(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${SESSION_HINT_COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Lax`;
}

interface RequestOptions extends Omit<RequestInit, "body"> {  body?: BodyInit | null;
  /** Send the CSRF token with the request (required for state changes). */
  csrf?: boolean;
  /** Query string parameters. */
  query?: Record<string, string | number | undefined | null>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { csrf = false, query, headers, body, ...rest } = options;

  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has("Accept")) {
    requestHeaders.set("Accept", "application/json");
  }
  if (csrf) {
    const token = readCookie(CSRF_COOKIE_NAME);
    if (token) {
      requestHeaders.set("X-CSRF-Token", token);
    }
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      ...rest,
      headers: requestHeaders,
      body,
      credentials: "include",
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Could not reach the Planet Health API. Check your connection and try again.",
      error,
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = "REQUEST_FAILED";
  let message = `The request failed with status ${response.status}.`;
  let details: unknown;

  try {
    const payload = (await response.json()) as ApiErrorBody;
    if (payload?.error) {
      code = payload.error.code ?? code;
      message = payload.error.message ?? message;
      details = payload.error.details;
    }
  } catch {
    // Non-JSON error body — keep the generic message.
  }

  if (response.status === 401) {
    clearSessionHint();
  }

  return new ApiError(response.status, code, message, details);
}

/* -------------------------------------------------------------------------- */
/* Authentication                                                              */
/* -------------------------------------------------------------------------- */

export interface RegisterInput {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginInput {
  email: string;
  password: string;
  remember?: boolean;
}

export const authApi = {
  register: (input: RegisterInput) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  login: (input: LoginInput) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),

  logout: () =>
    request<{ message: string }>("/auth/logout", { method: "POST", csrf: true }),

  me: () => request<User>("/auth/me"),

  refresh: () =>
    request<AuthResponse>("/auth/refresh", { method: "POST", csrf: true }),

  updateProfile: (input: { full_name: string }) =>
    request<User>("/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      csrf: true,
    }),

  changePassword: (input: {
    current_password: string;
    new_password: string;
    confirm_new_password: string;
  }) =>
    request<{ message: string }>("/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      csrf: true,
    }),

  forgotPassword: (email: string) =>
    request<{ message: string; delivery_available: boolean }>(
      "/auth/forgot-password",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      },
    ),
};

/* -------------------------------------------------------------------------- */
/* Analysis                                                                    */
/* -------------------------------------------------------------------------- */

export interface PredictionResult {
  prediction: Prediction;
  analysisId: string | null;
}

export const analysisApi = {
  /** Upload an image and run both models. */
  async predict(file: File): Promise<PredictionResult> {
    const form = new FormData();
    form.append("file", file);

    const url = new URL(`${API_BASE_URL}/analysis/predict`, window.location.origin);
    const token = readCookie(CSRF_COOKIE_NAME);
    const headers = new Headers();
    if (token) headers.set("X-CSRF-Token", token);

    let response: Response;
    try {
      response = await fetch(url.toString(), {
        method: "POST",
        headers,
        body: form,
        credentials: "include",
        cache: "no-store",
      });
    } catch (error) {
      throw new ApiError(
        0,
        "NETWORK_ERROR",
        "Could not reach the Planet Health API. Check your connection and try again.",
        error,
      );
    }

    if (!response.ok) {
      throw await toApiError(response);
    }

    const prediction = (await response.json()) as Prediction;
    return {
      prediction,
      analysisId: response.headers.get("X-Analysis-Id"),
    };
  },

  list: (options: { page?: number; pageSize?: number } = {}) =>
    request<PaginatedAnalyses>("/analysis", {
      query: {
        page: options.page ?? 1,
        page_size: options.pageSize ?? 20,
      },
    }),

  get: (id: string) => request<AnalysisDetail>(`/analysis/${id}`),
};

/* -------------------------------------------------------------------------- */
/* Dashboard & models                                                          */
/* -------------------------------------------------------------------------- */

export const dashboardApi = {
  stats: () => request<DashboardStats>("/dashboard/stats"),
};

export const modelsApi = {
  status: () => request<ModelStatus>("/models/status"),
};
