# Planet Health — Instructions for Chris

This document describes, step by step, how to move the **existing trained
models** into the Planet Health application.

> **Current state:** the repository contains the complete application, but it
> **does not contain any model files**. `backend/inference.py` has not been
> transferred yet, and neither `growth_model.pth` nor `stress_model.pth` is
> present. The application starts, serves every endpoint and answers
> `503` on the prediction endpoint until the three files below are in place.
>
> **Nothing in this document has been done yet.** Every step is written as
> something *you* do.

---

## 1. The two-phase workflow

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | Full application: frontend, backend, auth, database, dashboard, upload UI, history, settings, Docker Compose, docs. Runs without the models. | ✅ Complete |
| **Phase 2** | Transfer the three ML files, verify checkpoint paths, confirm CPU inference, wire real predictions into the UI. | ⏳ Waiting on you |

**Phase 1 must be finished and verified before Phase 2 begins.** The
application is deliberately built so that Phase 2 is a *file copy* plus a
verification pass — no restructuring, no rewrites, no new model code.

---

## 2. What already exists in the original research project

The original research project already contains a working, smoke-tested
inference implementation. **Do not rebuild it.**

```text
<original research project>/
├── artifacts/
│   ├── stress/
│   │   └── stress_model.pth      <-- trained checkpoint
│   └── growth/
│       └── growth_model.pth      <-- trained checkpoint
└── backend/
    └── inference.py               <-- working inference helper
```

`backend/inference.py` imports only `torch`, `torchvision` and `Pillow`. It
does **not** depend on a local model class, `timm` or `utils.py`. It exposes:

```python
load_models(growth_checkpoint=..., stress_checkpoint=..., device=None) -> PlantModels
predict_image(image, models_bundle) -> dict
```

It already handles EXIF orientation, RGB conversion, resizing to 224 × 224,
ImageNet normalisation taken from the checkpoints, CPU/CUDA selection and
returns JSON-serialisable predictions.

---

## 3. The three files you must transfer

| # | Original location | Destination in this repository |
|---|---|---|
| 1 | `<research>/backend/inference.py` | `backend/inference.py` |
| 2 | `<research>/artifacts/growth/growth_model.pth` | `backend/models/growth/growth_model.pth` |
| 3 | `<research>/artifacts/stress/stress_model.pth` | `backend/models/stress/stress_model.pth` |

Copy them with plain file operations — do not edit their contents:

```bash
# from the repository root
cp <research>/backend/inference.py            backend/inference.py
cp <research>/artifacts/growth/growth_model.pth backend/models/growth/growth_model.pth
cp <research>/artifacts/stress/stress_model.pth backend/models/stress/stress_model.pth
```

**Never create dummy or placeholder `.pth` files.** The backend checks that
each checkpoint exists *and* is a real file before it reports the models as
ready.

---

## 4. Git LFS or external artifact storage — decide before you copy

The original research project's `.gitignore` ignores the whole `artifacts/`
directory, so the checkpoints are **not** part of a normal Git clone. This
repository's `.gitattributes` already contains Git LFS rules for `*.pth`
(`filter=lfs diff=lfs merge=lfs -text`), and `.gitignore` excludes the
checkpoint binaries from plain Git objects.

Two supported options:

### Option A — Git LFS (recommended for this repository)

Git LFS 3.5.1 is already installed on this machine.

```bash
cd <planet-health-repo>
git lfs install
git lfs track "backend/models/**/*.pth"
git add .gitattributes
git commit -m "chore: track model checkpoints with Git LFS"
```

Then copy the checkpoints in and verify LFS picked them up:

```bash
cp <research>/artifacts/growth/growth_model.pth backend/models/growth/
cp <research>/artifacts/stress/stress_model.pth backend/models/stress/

git add backend/models
git lfs ls-files          # both .pth files must be listed
git commit -m "feat: add trained model checkpoints"
```

Cloning a fresh copy then requires `git lfs install` once before
`git lfs pull`.

### Option B — External artifact storage

If you would rather not put the binaries in Git at all:

1. Upload `growth_model.pth` and `stress_model.pth` to your artifact store
   (S3, GCS, Azure Blob, Hugging Face, an internal mirror …).
2. **Remove** the `*.pth filter=lfs …` lines from `.gitattributes` so the
   repository does not advertise LFS tracking it does not use.
3. Keep the `.gitignore` entries for `*.pth` so a local copy is never
   committed by accident.
4. Make the checkpoints available to the container at
   `backend/models/growth/growth_model.pth` and
   `backend/models/stress/stress_model.pth` before starting the backend
   (a download step in your deployment pipeline, or the bind mount already
   configured in `docker-compose.yml`).

Whichever option you choose, document the decision in this file and update
the *Model artifact delivery* row of the deployment checklist in
`README.md`.

---

## 5. Checkpoint paths are configurable — no need to edit `inference.py`

`backend/services/model_service.py` calls the transferred helper with
explicit paths, so the default checkpoint paths inside `inference.py` (which
point at the old `artifacts/…` layout) are **never used**:

```python
load_models(
    growth_checkpoint="<repo>/backend/models/growth/growth_model.pth",
    stress_checkpoint="<repo>/backend/models/stress/stress_model.pth",
)
```

The paths come from environment variables and default to the correct
locations inside this repository:

| Variable | Default |
|---|---|
| `MODEL_GROWTH_CHECKPOINT` | `models/growth/growth_model.pth` (relative to `backend/`) |
| `MODEL_STRESS_CHECKPOINT` | `models/stress/stress_model.pth` (relative to `backend/`) |

If you prefer absolute paths, set them in `backend/.env` or in the root
`.env` used by Docker Compose.

**Important:** `backend/inference.py` must not be modified. If it *is*
modified, keep the `load_models(...)` and `predict_image(...)` signatures
and the returned dictionary exactly as they are — the backend, the database
schema and the frontend all depend on that contract.

---

## 6. Install the runtime dependencies

The PyTorch runtime is deliberately kept out of the core requirements file so
that the application can run without it.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ml.txt
```

`requirements-ml.txt` already points at the PyTorch **CPU** wheel index, so
the multi-gigabyte CUDA builds are not pulled in. For a GPU, swap the index
for `https://download.pytorch.org/whl/cu121`:

```bash
pip install torch==2.9.1 torchvision==0.24.1 \
    --index-url https://download.pytorch.org/whl/cu121
```

Keep the `torch` / `torchvision` pair in sync — `torchvision 0.24.x` targets
`torch 2.9.x`.

With Docker the runtime is installed automatically unless you set
`INSTALL_ML_DEPS=false`:

```bash
# in the repository root .env
INSTALL_ML_DEPS=true
```

---

## 7. Verify the model loading (step by step)

### 7.1 Import check — does `inference.py` load?

```bash
cd backend
python -c "import inference; print(inference.load_models); print(inference.predict_image)"
```

Expected: two function objects, no exception.

### 7.2 Checkpoint paths

```bash
ls -lh backend/models/growth/growth_model.pth backend/models/stress/stress_model.pth
```

Both files must exist and be non-empty (a ResNet-18 checkpoint is roughly
45 MB).

### 7.3 Load the models directly

```bash
cd backend
python - <<'PY'
from inference import load_models

bundle = load_models(
    growth_checkpoint="models/growth/growth_model.pth",
    stress_checkpoint="models/stress/stress_model.pth",
)
print("models loaded:", type(bundle).__name__)
print("device:", getattr(bundle, "device", "unknown"))
PY
```

Expected: the bundle is printed with no traceback, on CPU by default.

### 7.4 CPU inference on a real image

```bash
cd backend
python - <<'PY'
import json
from inference import load_models, predict_image

bundle = load_models(
    growth_checkpoint="models/growth/growth_model.pth",
    stress_checkpoint="models/stress/stress_model.pth",
)
result = predict_image("path/to/a/real/leaf.jpg", bundle)
print(json.dumps(result, indent=2))
PY
```

Use a genuine plant photograph (the research project used a GroMo25 sample).
This is the same call the API makes.

---

## 8. Verify the exact API response

Start the backend:

```bash
cd backend
alembic upgrade head
uvicorn main:app --reload --port 8000
```

In a second terminal, register a user and run a prediction:

```bash
# 1. register
curl -s -c cookies.txt -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Chris","email":"chris@example.com","password":"Greenhouse1","confirm_password":"Greenhouse1"}'

# 2. read the CSRF token out of the cookie jar
CSRF=$(grep ph_csrf cookies.txt | awk '{print $7}')

# 3. upload an image
curl -s -b cookies.txt -X POST http://localhost:8000/api/analysis/predict \
  -H "X-CSRF-Token: $CSRF" \
  -F "file=@path/to/leaf.jpg" \
  -D headers.txt
```

The response body must be **exactly** this shape:

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

(The numbers above are illustrative — yours will differ.)

The response also carries two headers:

| Header | Purpose |
|---|---|
| `X-Analysis-Id` | The UUID of the stored analysis. The frontend uses it to open the results page. |
| `Location` | `/api/analysis/<id>` |

The body is intentionally **unchanged** from `predict_image()` so that the
contract with the original research project is preserved. Do not add fields
to it without versioning the API.

---

## 9. Switch the backend from *model-unavailable* to *model-ready*

There is no flag to flip. The backend decides automatically:

1. **Model status endpoint** — check what the backend thinks:

   ```bash
   curl -s http://localhost:8000/api/models/status
   ```

   | Response | Meaning |
   |---|---|
   | `{"status": "not_configured", "code": "MODEL_NOT_CONFIGURED", "available": false}` | `inference.py` or a checkpoint is missing. |
   | `{"status": "loading", "code": "MODEL_LOADING", "available": false}` | The checkpoints are still being read. |
   | `{"status": "failed", "code": "MODEL_LOAD_FAILED", "available": false}` | The checkpoints were found but could not be loaded — read the backend log. |
   | `{"status": "ready", "code": "MODEL_READY", "available": true}` | Inference is available. |

2. **Restart the backend** after copying the files in. The models are loaded
   **once**, during the FastAPI lifespan — they are never reloaded per
   request, and a copy performed while the server is running is not picked up
   until it restarts.

3. **Docker:** the `backend/models` directory is bind-mounted read-only into
   the container, so a plain file copy is enough:

   ```bash
   cp <research>/artifacts/growth/growth_model.pth backend/models/growth/
   cp <research>/artifacts/stress/stress_model.pth backend/models/stress/
   docker compose restart backend
   curl -s http://localhost:8000/api/models/status
   ```

4. **Expected behaviour before the copy** — the prediction endpoint must
   answer:

   ```http
   HTTP/1.1 503 Service Unavailable

   {
     "error": {
       "code": "MODEL_NOT_CONFIGURED",
       "message": "Plant analysis models are not configured."
     }
   }
   ```

   If it answers with anything else, something is wrong — investigate before
   continuing.

---

## 10. Frontend verification checklist

With the backend running and the models loaded:

- [ ] Open the dashboard — the upload card shows **no** "model integration is
      pending" banner.
- [ ] Upload a real leaf photograph. The card shows *Analyzing plant image…*
      while the request is in flight and the button is disabled.
- [ ] The browser is redirected to `/dashboard/analysis/<uuid>`.
- [ ] The results page shows the classification, the healthy / stressed
      probabilities, the **model stress probability**, the estimated leaf
      count and the estimated age in days.
- [ ] The dashboard summary cards increment (total, healthy, stressed, recent).
- [ ] The new row appears in `/dashboard/history`.
- [ ] Reloading the results page shows the same values (they are read from
      PostgreSQL, not from client state).
- [ ] Uploading a second account's analysis id returns `404` — records are
      scoped to their owner.
- [ ] The stored row contains prediction values and a timestamp only — no
      image binary.

---

## 11. Deployment readiness checklist

The production target is still undecided. Confirm these before deploying:

- [ ] **Frontend hosting** — a Node.js runtime capable of `next start`
      (Vercel, a container platform, or a VM).
- [ ] **Backend hosting** — Python 3.11+ with enough RAM for two ResNet-18
      models. Measure the real footprint with `docker stats` before choosing
      a machine size.
- [ ] **PostgreSQL hosting** — managed (Neon, RDS, Cloud SQL) or a container.
- [ ] **Reverse proxy** — expose `/api/*` under the frontend origin so the
      session cookie stays same-site. The Next.js route handler at
      `src/app/api/[...path]/route.ts` already does this; a production
      reverse proxy can point `/api/` straight at the backend instead.
- [ ] **Model artifact delivery** — Git LFS pull or an artifact download step
      in the deployment pipeline (see section 4).
- [ ] **CPU / RAM** — confirm actual latency and memory on the target
      machine. `INFERENCE_MAX_CONCURRENCY=1` is the safe default; raise it
      only after measuring.
- [ ] **Environment variables and secrets** — `SECRET_KEY` must be unique and
      random; `COOKIE_SECURE=true` once HTTPS is in place; `APP_ENV=production`
      makes the backend refuse the default secret.
- [ ] **Storage requirements** — none for images. PostgreSQL stores only
      users, sessions and prediction values.
- [ ] **TLS and a reverse-proxy trust header** — the backend honours
      `X-Forwarded-For` for rate limiting.

---

## 12. Useful commands

```bash
# Run the backend test-suite (does not need the models)
cd backend && python -m pytest -q

# Backend logs with model loading
cd backend && uvicorn main:app --reload --port 8000

# Full local stack
docker compose up --build

# Tear the stack down (keeps the database volume)
docker compose down

# Tear the stack down and delete the database volume
docker compose down -v

# Check the frontend build
cd frontend && npm ci && npm run typecheck && npm run build
```

---

## 13. If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `MODEL_NOT_CONFIGURED` after copying the files | The backend was not restarted | `docker compose restart backend` |
| `MODEL_NOT_CONFIGURED` and the paths look wrong | Relative paths resolve against the process working directory | Set absolute `MODEL_GROWTH_CHECKPOINT` / `MODEL_STRESS_CHECKPOINT` |
| `MODEL_LOAD_FAILED` | The checkpoint does not match the architecture in `inference.py`, or torch/torchvision are missing | Read the backend log; check the torch/torchvision version pair |
| `ModuleNotFoundError: No module named 'torch'` | The ML runtime was not installed | `pip install -r requirements-ml.txt` or set `INSTALL_ML_DEPS=true` and rebuild |
| `INFERENCE_FAILED` (HTTP 500) | The model raised during inference | Check the backend log; the original error type is recorded in `error.details.reason` |
| `INFERENCE_TIMEOUT` (HTTP 504) | Inference exceeded `INFERENCE_TIMEOUT_SECONDS` | Raise the timeout or use a smaller image |
| `MODEL_BUSY` (HTTP 503) | Another inference job is already running | Retry; raise `INFERENCE_MAX_CONCURRENCY` only if RAM allows |

---

## 14. What must **not** change

These are load-bearing and are covered by the acceptance criteria:

1. Do not retrain, fine-tune or re-architect either model.
2. Do not replace the checkpoint weights.
3. Do not overwrite `backend/inference.py` with a stub or a re-implementation.
4. Do not fabricate predictions — the API must never return a synthetic
   result when the models are unavailable.
5. Do not change the successful prediction JSON shape (`stress` / `growth`)
   without versioning the API and updating the frontend and the database.
6. Do not start persisting uploaded images without agreeing the storage
   provider, access control, retention period and deletion process first.
