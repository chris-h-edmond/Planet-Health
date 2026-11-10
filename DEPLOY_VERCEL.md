# Deploy Planet Health as one Vercel project

Vercel Services can deploy this Next.js frontend and FastAPI backend from this repository to one project and one domain. Services are currently in beta and must be enabled in the Vercel project settings.

## Before deployment

1. Push this repository to GitHub/GitLab/Bitbucket. Never commit `.env`; copy values from `.env.example` into Vercel Environment Variables instead.
2. Import the repository into Vercel. Set the project framework to **Services**. Keep the project root at the repository root so Vercel can read `vercel.json`.
3. The backend service installs `backend/requirements-ml.txt`, which selects CPU-only PyTorch and torchvision and includes the existing model checkpoints from `backend/models/`.
4. Configure the environment variables below for Production (and Preview if desired).
5. Deploy and check `/health`, `/api/models/status`, login, registration and an image prediction.

## Required backend environment variables

Set these under the Vercel project environment variables:

- `APP_ENV=production`
- `SECRET_KEY` — generate a unique, long random secret. Do not reuse the example value.
- `DATABASE_URL` — external PostgreSQL connection URL using SQLAlchemy's `postgresql+psycopg://` scheme. Use a managed database with TLS and serverless-friendly pooling.
- `COOKIE_SECURE=true`
- `ALLOWED_ORIGINS=https://YOUR-VERCEL-DOMAIN`
- `CORS_ALLOW_ORIGINS=https://YOUR-VERCEL-DOMAIN`
- `MAX_UPLOAD_SIZE_MB=4`
- `DB_POOL_SIZE=1`
- `DB_MAX_OVERFLOW=0`
- `MODEL_LOAD_ON_STARTUP=true`
- `MODEL_DEVICE=cpu`

Replace the example domain with the production domain, and add any preview/custom domains where applicable. `PUBLIC_APP_URL` should be set to the production URL if password reset emails are enabled. Configure `EMAIL_DELIVERY_ENABLED`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` only when SMTP delivery is set up.

## Required frontend build variable

Set `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB=4` for Production and Preview, then redeploy. The browser already calls `/api`; the top-level Vercel rewrite sends `/api/*` directly to FastAPI. The existing Next.js API proxy remains useful for local development, so no application route changes are required.

Vercel Functions accept request/response bodies up to 4.5 MB. The 4 MB file cap leaves room for multipart form overhead. This Vercel-specific cap is lower than the local default of 10 MB.

## Database schema

Vercel does not run the Docker Compose database or automatically run Alembic migrations. Create the managed PostgreSQL database, then run `alembic upgrade head` from `backend/` against its `DATABASE_URL` before using the app. Use your provider's external connection string locally for that one-time command. Do not include database credentials in the repository.

## Function bundle and runtime limits

The two tracked checkpoints total about 89.6 MB. Vercel's standard Python function bundle limit is 500 MB uncompressed; this repository also includes CPU-only PyTorch and torchvision. Verify the backend build output size during the first deployment. If it exceeds 500 MB, enable Vercel Large Functions (public beta, up to 5 GB) for the project and redeploy. If that feature is unavailable on the account, keep the frontend on Vercel and host the FastAPI/PyTorch backend on a Python container service.

The default Hobby function memory is 2 GB / 1 vCPU and maximum duration is 300 seconds. That is plausible for these two ResNet-18 models and single-request concurrency, but actual cold-start and peak memory must be checked in a deployed preview. Function memory remains platform-managed on Hobby. If prediction exceeds the 300-second Hobby timeout or the 2 GB memory ceiling, move the backend to a container host or a suitable paid Vercel plan.

## Manual Vercel project settings

- Framework Preset: **Services** (required for `services` in `vercel.json`).
- Root Directory: repository root.
- Enable Large Functions only if Vercel reports the backend exceeds the standard Python bundle limit.
- Add the variables above and redeploy after changing build-time `NEXT_PUBLIC_*` values.

## Local validation

From the repository root, validate the JSON with `python -m json.tool vercel.json`. The normal local workflow remains Docker Compose or the separate frontend/backend development servers.
