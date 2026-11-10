# ---------------------------------------------------------------------------
# Planet Health â€” frontend container image
# ---------------------------------------------------------------------------

FROM node:22-alpine AS base
WORKDIR /app

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# The browser talks to the application origin; the API is proxied by the
# Next.js route handler at /api/[...path].
ARG NEXT_PUBLIC_API_URL=/api
ARG NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB=10
ARG NEXT_PUBLIC_CSRF_COOKIE_NAME=ph_csrf
ARG NEXT_PUBLIC_SESSION_HINT_COOKIE_NAME=ph_session_hint
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB=$NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB \
    NEXT_PUBLIC_CSRF_COOKIE_NAME=$NEXT_PUBLIC_CSRF_COOKIE_NAME \
    NEXT_PUBLIC_SESSION_HINT_COOKIE_NAME=$NEXT_PUBLIC_SESSION_HINT_COOKIE_NAME \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM base AS runner
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npm", "run", "start"]

