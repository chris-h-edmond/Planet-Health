# Planet Health

**Automated greenhouse climate control vision system.**

Planet Health is a full-stack, AI-assisted plant monitoring platform. Users
upload a photograph of a leaf and receive two machine-learning outputs from
two existing PyTorch research models:

1. **Plant stress classification** — *Healthy* or *Stressed*, with the model
   probability for each class.
2. **Plant growth estimation** — estimated leaf count and estimated plant age
   in days.

The application also keeps a per-user analysis history, exposes dashboard
statistics derived from real database records, and works in a light and a dark
theme.

> **Status:** the application is complete and fully functional. The trained
> model checkpoints are **not** part of this repository. Until they are
> transferred, the prediction endpoint answers with `HTTP 503` and the UI
> says so explicitly. See [`INSTRUCTIONS_TO_CHRIS.md`](./INSTRUCTIONS_TO_CHRIS.md).

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Quick start with Docker Compose](#quick-start-with-docker-compose)
- [Local development without Docker](#local-development-without-docker)
- [API overview](#api-overview)
- [Authentication](#authentication)
- [Model status and error contract](#model-status-and-error-contract)
- [Prediction response contract](#prediction-response-contract)
- [Image handling and storage policy](#image-handling-and-storage-policy)
- [Database schema](#database-schema)
- [Design system](#design-system)
- [Research limitations](#research-limitations)
- [Project layout](#project-layout)
- [Testing](#testing)

---

## Overview

```
┌───────────────┐        same origin        ┌──────────────────┐
│   Next.js 16  │  /api/*  ────────────────▶ │  Next.js proxy   │
│  (frontend)   │                           │  route handler   │
└───────────────┘                           └────────┬─────────┘
                                                     │  http://backend:8000
                                                     ▼
                                       ┌──────────────────────────────┐
                                       │         FastAPI              │
                                       │  api/  →  services/  →  db/  │
                                       │                    │         │
                                       │            model_service      │
                                       │                    │         │
                                       │            inference.py        │
                                       │            (PyTorch)          │
                                       └──────────────┬───────────────┘
                                                      │
                                                      ▼
                                            ┌──────────────────┐
                                            │   PostgreSQL 16  │
                                            └──────────────────┘
```

The browser only ever talks to the Next.js origin. The route handler at
`frontend/src/app/api/[...path]/route.ts` forwards API calls to FastAPI and
copies the response back — including `Set-Cookie` headers — so the session
cookie is stored for the application origin. That keeps the deployment
free of cross-domain cookie problems and means no secret is ever exposed to
the browser.

---

## Architecture

### Backend (`backend/`)

| Layer | Responsibility |
|---|---|
| `main.py` | Application factory, lifespan, middleware, exception handlers, `/health`. |
| `api/` | HTTP routes only — no business logic, no SQL, no ML. |
| `services/` | Business logic: authentication, sessions, analysis persistence, dashboard aggregation, model lifecycle. |
| `db/` | SQLAlchemy 2 models and the declarative base. |
| `schemas/` | Pydantic v2 request / response models. |
| `core/` | Configuration, engine/session factory, Argon2id hashing, error envelope, rate limiting, SMTP transport. |
| `services/model_service.py` | The **only** module that knows about the checkpoints. |
| `inference.py` | **Transferred in Phase 2** from the original research project. Untouched. |

Key decisions:

- **Models are loaded once**, in the FastAPI lifespan, and stored on the
  `ModelService` singleton. They are never reloaded per request.
- **Inference runs off the event loop.** The route handlers are synchronous
  (`def`), so FastAPI executes them in its worker threadpool. Inside the
  model service a dedicated `ThreadPoolExecutor` with
  `INFERENCE_MAX_CONCURRENCY` workers (default `1`) performs the PyTorch
  call, and a bounded semaphore rejects additional concurrent jobs with
  `503 MODEL_BUSY` instead of letting them exhaust memory.
- **Failures are explicit.** If the checkpoints are missing, the application
  still starts and serves every unrelated endpoint; only the prediction
  endpoint returns `503`.
- **One error envelope** for every failure:

  ```json
  { "error": { "code": "MODEL_NOT_CONFIGURED", "message": "…" } }
  ```

### Frontend (`frontend/`)

| Path | Responsibility |
|---|---|
| `src/app/` | App Router routes: landing, `/login`, `/register`, `/forgot-password`, `/dashboard/*`. |
| `src/app/api/[...path]/route.ts` | Same-origin API proxy. |
| `src/proxy.ts` | Optimistic route guard for `/dashboard/*`. |
| `src/components/ui/` | shadcn/ui-style primitives (Radix + CVA + Tailwind). |
| `src/components/dashboard/` | Dashboard shell, sidebar, top bar, stat cards, upload card, history table, settings. |
| `src/components/analysis/` | Stress and growth result panels. |
| `src/lib/api.ts` | The single API client — cookie handling, CSRF header, error normalisation. |
| `src/lib/types.ts` | Shared types that mirror the backend contract. |

All data loading is client-side, so the pages stay interactive and the
session cookie is always the source of truth.

---

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, shadcn/ui, Lucide icons, custom theme provider |
| Backend | Python 3.12, FastAPI, Pydantic v2, pydantic-settings |
| ML | PyTorch 2.9, torchvision 0.24, Pillow (CPU build by default) |
| Database | PostgreSQL 16, SQLAlchemy 2, Alembic |
| Auth | Argon2id (`argon2-cffi`), server-side sessions, HTTP-only cookies, double-submit CSRF |
| Dev environment | Docker, Docker Compose, Git (Git LFS prepared for the checkpoints) |

---

## Quick start with Docker Compose

### Requirements

- Docker Engine 24+ with the Compose v2 plugin (`docker compose version`).
- At least 4 GB of free memory.

### Start the stack

```bash
git clone <your-repository-url> planet-health
cd planet-health

cp .env.example .env          # optional — sensible development defaults exist
docker compose up --build
```

That single command starts three services:

| Service | URL | Notes |
|---|---|---|
| Frontend | <http://localhost:3000> | Next.js application |
| Backend | <http://localhost:8000> | FastAPI — interactive docs at `/docs` |
| PostgreSQL | `localhost:5432` | Data persists in the `postgres_data` volume |

The backend container runs `alembic upgrade head` before starting, so the
schema is created automatically.

### Stop the stack

```bash
docker compose down            # keeps the database volume
docker compose down -v         # also deletes the database volume
```

### Useful commands

```bash
docker compose logs -f backend
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
docker compose exec backend python -m pytest -q
docker compose exec db psql -U planethealth -d planethealth
docker compose restart backend      # pick up newly added model checkpoints
```

### Model checkpoints and Docker

`backend/models/` is bind-mounted read-only into the backend container, so the
checkpoints can be added in Phase 2 **without rebuilding the image**. See
[`INSTRUCTIONS_TO_CHRIS.md`](./INSTRUCTIONS_TO_CHRIS.md).

The PyTorch runtime is installed in the image by default. For a smaller,
faster image while the models are not yet installed, set this in `.env`:

```bash
INSTALL_ML_DEPS=false
```

---

## Local development without Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

pip install -r requirements.txt      # core API only
pip install -r requirements-dev.txt  # + pytest, httpx, ruff
# Optional: the ML runtime (needed in Phase 2)
pip install torch==2.9.1 torchvision==0.24.1 \
    --index-url https://download.pytorch.org/whl/cpu

cp .env.example .env                 # adjust DATABASE_URL
alembic upgrade head
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
cp .env.local.example .env.local     # optional
npm run dev
```

The Next.js development server proxies `/api/*` to `http://localhost:8000`.
Override the target with `INTERNAL_API_URL` if the backend runs elsewhere.

---

## API overview

Base URL: `http://localhost:8000` (or `/api` on the frontend origin).

| Method | Endpoint | Purpose | Auth |
|---|---|---|---|
| `GET` | `/health` | Application availability | — |
| `GET` | `/api/models/status` | Model availability | — |
| `POST` | `/api/auth/register` | Create an account | — |
| `POST` | `/api/auth/login` | Sign in | — |
| `POST` | `/api/auth/logout` | Revoke the current session | ✔ |
| `GET` | `/api/auth/me` | The signed-in user (also refreshes the session) | ✔ |
| `POST` | `/api/auth/refresh` | Extend the session | ✔ |
| `PATCH` | `/api/auth/me` | Update the display name | ✔ |
| `POST` | `/api/auth/change-password` | Change the password | ✔ |
| `POST` | `/api/auth/forgot-password` | Request a reset email | — |
| `POST` | `/api/auth/reset-password` | Set a new password with a reset token | — |
| `POST` | `/api/analysis/predict` | Upload an image and run both models | ✔ |
| `GET` | `/api/analysis` | Paginated analysis history | ✔ |
| `GET` | `/api/analysis/{id}` | A single analysis owned by the caller | ✔ |
| `GET` | `/api/dashboard/stats` | Dashboard statistics | ✔ |

Interactive documentation is served at `/docs` (Swagger UI) and `/redoc`.

---

## Authentication

- **Argon2id** password hashing via `argon2-cffi`. Plain-text passwords are
  never stored or logged.
- **Server-side sessions.** The browser receives an opaque 32-byte random
  token in an HTTP-only cookie (`ph_session`). Only the SHA-256 digest of
  that token is stored in PostgreSQL, so a database leak does not expose
  usable credentials.
- **CSRF protection** uses the double-submit pattern: a readable
  `ph_csrf` cookie is echoed back in the `X-CSRF-Token` header for every
  state-changing request, and the `Origin` header is checked against the
  configured allow-list.
- **Session lifetime** is 12 hours by default and 30 days with *remember me*.
  Sessions refresh on a sliding window (`SESSION_REFRESH_INTERVAL_SECONDS`).
- **Rate limiting** is applied to the authentication endpoints — 8 login
  attempts per IP+email per 5 minutes, 5 registrations per IP per hour.
- **Cookie flags**: `HttpOnly` on the session cookie, `SameSite=Lax` by
  default, `Secure` once the deployment is behind HTTPS
  (`COOKIE_SECURE=true`).
- **Session marker**: a readable `ph_session_hint` cookie tells the browser
  that a session *may* exist, so an anonymous visitor does not trigger a 401
  round trip on every page load. It carries no authority — the HTTP-only
  session cookie remains the only credential.
- **Ownership** is enforced in the database layer: analysis queries are
  always filtered by `user_id`, so another account's analysis id returns
  `404`, not `403`.

### Forgot password

Password reset requires a real SMTP transport.

- With `EMAIL_DELIVERY_ENABLED=false` — the default — the endpoint answers
  `503` with `EMAIL_DELIVERY_NOT_CONFIGURED` and the UI says plainly that
  the feature is unavailable. It never pretends that an email was sent.
- With SMTP configured, a single-use token is created, a reset link is
  **actually delivered** by SMTP, and `/reset-password` consumes the token
  and sets the new password. The response is identical for known and unknown
  addresses, so the endpoint cannot be used to enumerate accounts.

Reset tokens expire after 60 minutes, can only be used once, invalidate the
previous outstanding links for the account, and are stored only as a SHA-256
digest. Resetting a password revokes every existing session.

---

## Model status and error contract

`GET /api/models/status` tells the frontend whether inference is possible:

```json
{
  "status": "not_configured",
  "code": "MODEL_NOT_CONFIGURED",
  "available": false,
  "availability": "unavailable",
  "message": "Plant analysis models are not configured.",
  "detail": "backend/inference.py has not been transferred into this repository yet.",
  "models": { "stress": false, "growth": false },
  "device": "unavailable",
  "checkpoints": {
    "stress": "…/backend/models/stress/stress_model.pth",
    "growth": "…/backend/models/growth/growth_model.pth"
  }
}
```

| `status` | `code` | Meaning |
|---|---|---|
| `not_configured` | `MODEL_NOT_CONFIGURED` | `inference.py` or a checkpoint file is missing. |
| `loading` | `MODEL_LOADING` | The checkpoints are still being read. |
| `ready` | `MODEL_READY` | Inference is available. |
| `failed` | `MODEL_LOAD_FAILED` | The checkpoints were found but could not be loaded. |

While the models are unavailable, the prediction endpoint returns:

```http
HTTP/1.1 503 Service Unavailable

{
  "error": {
    "code": "MODEL_NOT_CONFIGURED",
    "message": "Plant analysis models are not configured."
  }
}
```

Once the models are ready, a failure *inside* a single prediction is reported
separately — `INFERENCE_FAILED` (500), `INFERENCE_TIMEOUT` (504) or
`MODEL_BUSY` (503) — so a model failure is never confused with a missing
model.

---

## Prediction response contract

`POST /api/analysis/predict` accepts `multipart/form-data` with a `file`
field and returns **exactly** the output of the existing
`predict_image()` helper:

```json
{
  "stress": {
    "label": "Stressed",
    "stress_score": 0.87,
    "score_scale": "0-1",
    "probabilities": {
      "healthy": 0.13,
      "stressed": 0.87
    }
  },
  "growth": {
    "leaf_count": 8.4,
    "leaf_count_rounded": 8,
    "age_days": 26.2
  }
}
```

The values above are illustrative.

The identifier of the stored analysis is returned in the response headers so
that the body stays byte-compatible with the research contract:

| Header | Value |
|---|---|
| `X-Analysis-Id` | `5d0f…` — the UUID of the stored analysis |
| `Location` | `/api/analysis/5d0f…` |

`GET /api/analysis/{id}` returns the stored record in the same `stress` /
`growth` shape plus the `id` and `created_at` metadata.

**Interpretation.**

- `stress_score` is the softmax probability of the **Stressed** class — the
  model's confidence, **not** a validated measurement of biological stress
  severity. The UI labels it *"Model stress probability"*.
- `leaf_count` is the continuous regression output; `leaf_count_rounded` is
  the display value. The UI shows the rounded number prominently.
- `age_days` is an experimental estimate. The current growth-model validation
  reports an **Age MAE of approximately 15.6 days**, so the UI always marks
  it as experimental.

---

## Image handling and storage policy

**Uploaded images are not retained.** The workflow is:

1. The frontend previews the selected file locally (an object URL — nothing
   is uploaded yet).
2. On submit the file is sent as `multipart/form-data`.
3. The backend reads it into memory, enforcing the size limit while reading.
4. The payload is validated: the declared content type must be
   `image/jpeg` or `image/png`, the bytes must actually decode as JPEG or
   PNG, the declared type must match the detected type, and the decoded
   image must stay inside the pixel budget (decompression-bomb guard).
5. The models run and the prediction values are stored.
6. The image bytes are discarded.

Only prediction values and timestamps are written to PostgreSQL — there is no
image column anywhere in the schema.

If image retention is wanted later, the storage provider, access control,
retention period and deletion process must be agreed first.

---

## Database schema

Created by Alembic (`backend/alembic/versions/0001_initial_schema.py`).

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | `INTEGER` | Primary key |
| `full_name` | `VARCHAR(150)` | |
| `email` | `VARCHAR(320)` | Unique, indexed, stored lower-cased |
| `password_hash` | `VARCHAR(255)` | Argon2id hash |
| `created_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |

### `user_sessions`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` | Primary key |
| `user_id` | `INTEGER` | FK → `users.id`, `ON DELETE CASCADE` |
| `token_hash` | `VARCHAR(64)` | SHA-256 of the session token, unique |
| `csrf_token_hash` | `VARCHAR(64)` | SHA-256 of the CSRF token |
| `remember` | `BOOLEAN` | |
| `expires_at` | `TIMESTAMPTZ` | Indexed |
| `last_seen_at` | `TIMESTAMPTZ` | Sliding-refresh bookkeeping |
| `created_at` | `TIMESTAMPTZ` | |
| `user_agent` | `VARCHAR(255)` | |
| `ip_address` | `VARCHAR(64)` | |

### `password_reset_tokens`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` | Primary key |
| `user_id` | `INTEGER` | FK → `users.id`, `ON DELETE CASCADE` |
| `token_hash` | `VARCHAR(64)` | SHA-256 of the reset token, unique |
| `expires_at` | `TIMESTAMPTZ` | Indexed — 60 minute lifetime |
| `used_at` | `TIMESTAMPTZ` | Set when the token is consumed |
| `created_at` | `TIMESTAMPTZ` | |

### `analyses`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` | Primary key |
| `user_id` | `INTEGER` | FK → `users.id`, `ON DELETE CASCADE` |
| `stress_label` | `VARCHAR(16)` | `Healthy` / `Stressed` |
| `stress_score` | `DOUBLE` | Probability of the Stressed class |
| `score_scale` | `VARCHAR(8)` | `0-1` |
| `healthy_probability` | `DOUBLE` | |
| `stressed_probability` | `DOUBLE` | |
| `leaf_count` | `DOUBLE` | Continuous estimate |
| `leaf_count_rounded` | `INTEGER` | Display value |
| `age_days` | `DOUBLE` | Estimate in days |
| `created_at` | `TIMESTAMPTZ` | Indexed |

Indexes: `ix_analyses_user_id`, `ix_analyses_user_created_at`,
`ix_analyses_user_stress_label`.

**No image binary data is stored.**

Dashboard statistics (`/api/dashboard/stats`) are always aggregated from
these records — total analyses, healthy count, stressed count, analyses in
the last 7 days, healthy rate, average stress score and the timestamp of the
most recent analysis. Nothing is hardcoded.

---

## Design system

The palette is defined once in `frontend/src/app/globals.css` as CSS custom
properties and mapped into Tailwind through `@theme inline`, so every
component supports both themes automatically.

| Purpose | Light | Dark |
|---|---|---|
| Primary | `#276749` | `#3F9E70` |
| Background | `#F7F9F7` | `#111714` |
| Surface | `#FFFFFF` | `#1A241E` |
| Foreground | `#17231C` | `#E8F0EA` |
| Muted foreground | `#5F6F65` | `#8D9D93` |
| Warning | `#D99B43` | `#E0AD5D` |
| Error | `#D66A6A` | `#E08585` |

- The theme is stored in `localStorage` and the system preference is
  respected on a first visit. An inline script in the document `<head>`
  applies the theme **before the first paint**, so there is **no flash of the
  wrong theme**. The React state is synchronised with the document through
  `useSyncExternalStore`, which keeps the server render and the first client
  render identical and avoids a hydration mismatch.
- Light and dark are both designed for WCAG AA contrast; the muted foreground
  shade was adjusted from the original brief for that reason.
- Layouts are responsive from 320 px upwards. The dashboard sidebar becomes a
  slide-over drawer below the `lg` breakpoint, and tables collapse into
  cards on small screens.

---

## Research limitations

The models behind Planet Health are **experimental research models**.

- They have been verified to **execute correctly** on CPU, but they have not
  been scientifically validated for field deployment.
- The growth model's age prediction carries an **MAE of roughly 15.6 days**.
  It must not be presented as a reliable measurement.
- The stress score is the model's probability for the *Stressed* class. It is
  a confidence value, **not** a validated severity measurement.
- Every results screen carries the disclaimer: *"These results are
  AI-generated estimates from experimental computer-vision models. They
  should not replace direct plant inspection or validated agricultural
  assessment."*
- The application never fabricates a prediction. When the models are
  unavailable it says so and returns `503`.

---

## Project layout

```text
Planet-Health/
├── docker-compose.yml          # db + backend + frontend
├── .env.example                # root configuration for Docker Compose
├── .gitattributes              # Git LFS rules for *.pth
├── .gitignore
├── README.md
├── INSTRUCTIONS_TO_CHRIS.md    # Phase 2 — transferring the models
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt        # core runtime
│   ├── requirements-ml.txt     # + torch / torchvision
│   ├── alembic.ini
│   ├── main.py
│   ├── api/                    # auth, analysis, dashboard, models
│   ├── core/                   # config, database, security, errors, rate limit
│   ├── db/                     # ORM models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # business logic + model_service
│   ├── models/                 # growth/ and stress/ checkpoint directories
│   ├── alembic/                # migrations
│   └── tests/                  # pytest suite
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── next.config.ts
    └── src/
        ├── app/                # routes
        ├── components/         # ui, dashboard, analysis, site, auth
        ├── hooks/
        ├── lib/                # api client, types, formatting
        └── proxy.ts            # route guard
```

---

## Testing

```bash
# Backend — 38 tests, no models required
cd backend && python -m pytest -q

# Backend — lint
cd backend && ruff check .

# Frontend — type safety, lint and production build
cd frontend && npm run typecheck && npm run lint && npm run build
```

The backend suite covers registration and validation, Argon2id hashing,
login and logout, HTTP-only cookie flags, CSRF enforcement, protected routes,
cross-account isolation of analyses, dashboard statistics derived from real
records, image validation (wrong type, mislabelled payload), the model
status endpoint, the `503` behaviour when the models are absent, and the
complete password reset flow including single-use tokens.

---

## Licence and attribution

Planet Health wraps existing research models. The models, their training
data and their evaluation belong to the original research project.
