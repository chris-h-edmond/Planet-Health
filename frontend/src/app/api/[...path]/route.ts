/**
 * Same-origin API proxy.
 *
 * The browser only ever talks to the Next.js origin (`/api/...`).  This route
 * handler forwards the request to the FastAPI backend and copies the response
 * back, including `Set-Cookie` headers, so that the session and CSRF cookies
 * are stored for the application origin.
 *
 * Environment variables
 * ---------------------
 * INTERNAL_API_URL   Base URL of the FastAPI backend.
 *                    Default: http://localhost:8000 (local development).
 *                    In Docker Compose this is http://backend:8000.
 */

import { NextResponse, type NextRequest } from "next/server";

const BACKEND_URL = (
  process.env.INTERNAL_API_URL ??
  process.env.BACKEND_URL ??
  "http://localhost:8000"
).replace(/\/$/, "");

const FORWARDED_REQUEST_HEADERS = [
  "accept",
  "accept-language",
  "content-type",
  "cookie",
  "user-agent",
  "x-csrf-token",
  "x-requested-with",
];

const FORWARDED_RESPONSE_HEADERS = [
  "cache-control",
  "content-type",
  "location",
  "x-analysis-id",
  "x-request-id",
];

async function handler(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const incoming = new URL(request.url);

  const target = new URL(`${BACKEND_URL}/api/${path.join("/")}`);
  target.search = incoming.search;

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  headers.set("x-forwarded-host", incoming.host);
  headers.set("x-forwarded-proto", incoming.protocol.replace(":", ""));

  // Preserve the original client address so that the backend can rate limit
  // per client rather than per proxy.
  const forwardedFor =
    request.headers.get("x-forwarded-for") ??
    request.headers.get("x-real-ip");
  if (forwardedFor) {
    headers.set("x-forwarded-for", forwardedFor);
  }

  let body: ArrayBuffer | undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target.toString(), {
      method: request.method,
      headers,
      body: body && body.byteLength > 0 ? body : undefined,
      redirect: "manual",
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "BACKEND_UNAVAILABLE",
          message:
            "The Planet Health API could not be reached. Please try again in a moment.",
        },
      },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  responseHeaders.set("cache-control", "no-store");

  // `Set-Cookie` may appear more than once (session cookie + CSRF cookie).
  for (const cookie of upstream.headers.getSetCookie()) {
    responseHeaders.append("set-cookie", cookie);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const HEAD = handler;
export const OPTIONS = handler;
