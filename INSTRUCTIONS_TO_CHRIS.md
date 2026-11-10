# Planet Health — Phase 2 Completion Record & Operating Guide

This document records the completed integration of the trained models and
explains how to operate, verify and troubleshoot them.

> **Phase 2 status: complete.** Both checkpoints and the working
> `backend/inference.py` are tracked in this repository, the models load once
> during the FastAPI startup, and the dashboard returns real predictions.
> Neither model was retrained, recreated or modified.

---

## 1. What was transferred

| File | Original location | Size | State |
|---|---|---|---|
| `backend/inference.py` | `<research>/backend/inference.py` | 9 KB | **Unmodified** |
| `backend/models/growth/growth_model.pth` | `<research>/artifacts/growth/growth_model.pth` | 42.7 MB | Unmodified |
| `backend/models/stress/stress_model.pth` | `<research>/artifacts/stress/stress_model.pth` | 42.7 MB | Unmodified |

The research evaluation artefacts that accompanied the checkpoints were
included as well, because they document how the models were validated:

| File | Contents |
|---|---|
| `backend/models/growth/cv_metrics.json` | LeaveOnePlantOut cross-validation, per fold and overall |
| `backend/models/growth/cv_predictions.csv` | Per-image cross-validation predictions |
| `backend/models/growth/cv_plant_day_predictions.csv` | Per-plant/per-day cross-validation predictions |
| `backend/models/stress/metrics.json` | Split sizes and best validation accuracy |
| `backend/models/stress/training_history.csv` | Per-epoch loss and accuracy |

---

## 2. Git tracking — plain Git, no LFS

Git LFS is **not** used for this repository. The checkpoints are ordinary Git
blobs.

- `.gitignore` no longer contains any `*.pth` / `backend/models/**` rule. It
  still excludes `.env`, `__pycache__/`, `.venv/` and the other build and
  runtime artefacts.
- `.gitattributes` marks `*.pth` as `binary` so Git never applies text
  normalisation to it. The pre-existing `* text=auto` default is untouched.

Confirm the state:

```bash
git check-attr -a backend/models/growth/growth_model.pth
#  -> binary: set
#  -> diff: unset
#  -> merge: unset
#  -> text: unset      (no filter=lfs -> not an LFS pointer)

git ls-tree -r -l HEAD -- backend/models
#  -> blob 06e9cb1f…  44788043  backend/models/growth/growth_model.pth
#  -> blob bf46db45…  44790283  backend/models/stress/stress_model.pth
```

Both blobs are the real 44.8 MB checkpoints, not LFS pointers.

**Consequence:** a plain `git clone` contains everything needed to run
inference, and the repository is ~85 MB larger than the source tree.

---

## 3. How the checkpoint paths are configured

`backend/inference.py` was **not** edited. Its own defaults still point at
the research layout:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROWTH_CHECKPOINT = PROJECT_ROOT / "artifacts" / "growth" / "growth_model.pth"
```

Inside this repository that resolves to `/artifacts/…`, which does not exist.
It is never used, because `backend/services/model_service.py` calls the helper
with explicit keyword arguments:

```python
load_models(
    growth_checkpoint="<repo>/backend/models/growth/growth_model.pth",
    stress_checkpoint="<repo>/backend/models/stress/stress_model.pth",
)
```

The service inspects the signature of `load_models` and only passes the
arguments it accepts, so the transferred implementation keeps working
unchanged.

The paths themselves come from the environment:

| Variable | Default | Notes |
|---|---|---|
| `MODEL_GROWTH_CHECKPOINT` | `models/growth/growth_model.pth` | Relative paths resolve against the backend package root, never against the working directory. |
| `MODEL_STRESS_CHECKPOINT` | `models/stress/stress_model.pth` | Same. |

---

## 4. Dependency verification

The runtime needs `torch`, `torchvision` and `Pillow` — exactly what
`inference.py` imports. It does not depend on `timm`, a local model class or
`utils.py`.

```bash
cd backend
pip install -r requirements-ml.txt          # points at the PyTorch CPU index
```

Verified inside the container:

```text
torch 2.9.1+cpu | torchvision 0.24.1+cpu
```

The backend image installs the runtime when `INSTALL_ML_DEPS=true` (the
default). With `INSTALL_ML_DEPS=false` the application still starts, but the
models cannot be imported and the service reports `not_configured`.

---

## 5. Model lifecycle

| Stage | Behaviour |
|---|---|
| Startup | `load_models()` is called **once**, inside the FastAPI lifespan. |
| State | The returned `PlantModels` bundle is stored on the `ModelService` singleton, i.e. in application state. |
| Request | `predict_image(image_bytes, models_bundle)` runs the two checkpoints. |
| Threading | Route handlers are synchronous, so FastAPI runs them in its worker threadpool. Inside the service a dedicated `ThreadPoolExecutor` with `INFERENCE_MAX_CONCURRENCY` workers performs the PyTorch call, and a bounded semaphore refuses extra concurrent jobs with `MODEL_BUSY`. The event loop is never blocked. |
| Missing checkpoint | `not_configured` / `MODEL_NOT_CONFIGURED`; the prediction endpoint answers `503`. |
| Load failure | `failed` / `MODEL_LOAD_FAILED`; every unrelated endpoint keeps working. |
| Inference failure | `INFERENCE_FAILED` (500), `INFERENCE_TIMEOUT` (504) — always distinct from a *missing* model. |

### Verification performed

```text
one container restart   ->  1 x "Loading models (growth=…, stress=…, device=auto)"
20 consecutive predictions ->  0 additional loads
```

The bundle is therefore reused for every request and never reloaded.

---

## 6. Verification record

### 6.1 Model loading

```text
INFO  planethealth.models :: Model status changed to loading (Loading model checkpoints.)
INFO  planethealth.models :: Loading models (growth=/app/models/growth/growth_model.pth,
                               stress=/app/models/stress/stress_model.pth, device=auto)
INFO  planethealth.models :: Model status changed to ready (Plant analysis models are ready.)
INFO  planethealth :: Model service status: ready
```

`load_models()` returns a `PlantModels` bundle with `device=cpu` and the
preprocessing `Compose(Resize((224, 224)), ToTensor(), Normalize(ImageNet))`
read from the checkpoints.

### 6.2 `GET /api/models/status`

```json
{
  "status": "ready",
  "code": "MODEL_READY",
  "available": true,
  "availability": "available",
  "message": "Plant analysis models are ready.",
  "models": { "stress": true, "growth": true },
  "device": "cpu"
}
```

### 6.3 Real CPU inference — GroMo25 photographs

Images taken from the `MrigLabIITRopar/GroMo25` dataset the models were
trained on (12 MP phone photographs).

**`radish/p1/d1/L1` — ground truth: 2 leaves, day 1**

```json
{
  "stress": {
    "label": "Stressed",
    "stress_score": 0.9962108135223389,
    "score_scale": "0-1",
    "probabilities": { "healthy": 0.003789192298427224, "stressed": 0.9962108135223389 }
  },
  "growth": { "leaf_count": 1.0987526178359985, "leaf_count_rounded": 1, "age_days": 0.0 }
}
```

**`radish/p1/d25/L1` — ground truth: 10 leaves, day 25**

```json
{
  "stress": {
    "label": "Stressed",
    "stress_score": 0.9990670084953308,
    "score_scale": "0-1",
    "probabilities": { "healthy": 0.0009330280008725822, "stressed": 0.9990670084953308 }
  },
  "growth": { "leaf_count": 10.006080627441406, "leaf_count_rounded": 10, "age_days": 16.308734893798828 }
}
```

The response body is **exactly** the documented contract — the keys are
`stress.label`, `stress.stress_score`, `stress.score_scale`,
`stress.probabilities.healthy`, `stress.probabilities.stressed`,
`growth.leaf_count`, `growth.leaf_count_rounded` and `growth.age_days`, and
nothing else.

The leaf count is exact (10 predicted → 10 actual). The age estimate of
16.3 days against an actual 25 days sits inside the documented error band
(LeaveOnePlantOut image-level Age MAE 15.63 days).

The `Stressed` label is the model's genuine output for these photographs. It
has not been filtered, tuned or overridden.

### 6.4 Storage and retention

```text
SELECT column_name, data_type FROM information_schema.columns
 WHERE table_name = 'analyses';
 id | uuid                      created_at  | timestamp with time zone
 user_id | integer              stress_label | character varying
 stress_score | double precision  score_scale | character varying
 healthy_probability | double precision
 stressed_probability | double precision
 leaf_count | double precision   leaf_count_rounded | integer
 age_days | double precision
```

There is **no image column**, no `bytea` and no binary column anywhere in the
schema. A filesystem sweep of the running container found no uploaded image
file, and the database is 7.9 MB in total.

Uploaded images are read into memory, validated, processed and discarded.

### 6.5 Missing checkpoints

Moving both checkpoints aside and restarting the backend:

```text
GET /api/models/status
{ "status": "not_configured", "code": "MODEL_NOT_CONFIGURED", "available": false,
  "detail": "Missing checkpoint file(s): /app/models/growth/growth_model.pth,
             /app/models/stress/stress_model.pth" }

POST /api/analysis/predict  ->  HTTP 503
{ "error": { "code": "MODEL_NOT_CONFIGURED",
             "message": "Plant analysis models are not configured." } }
```

Restoring the checkpoints and restarting returns `ready` again.

---

## 7. Operating the models

### Replace a checkpoint

`backend/models/` is bind-mounted read-only into the container, so a plain
file copy is enough:

```bash
cp new_model.pth backend/models/growth/growth_model.pth
docker compose restart backend
curl -s http://localhost:8000/api/models/status
```

The models are loaded during startup, so a copy performed while the server is
running is only picked up after a restart.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `MODEL_GROWTH_CHECKPOINT` | `models/growth/growth_model.pth` | Growth checkpoint |
| `MODEL_STRESS_CHECKPOINT` | `models/stress/stress_model.pth` | Stress checkpoint |
| `MODEL_LOAD_ON_STARTUP` | `true` | Load the models during the FastAPI lifespan |
| `MODEL_DEVICE` | `auto` | `auto`, `cpu` or `cuda` |
| `INFERENCE_MAX_CONCURRENCY` | `1` | Simultaneous inference jobs |
| `INFERENCE_TIMEOUT_SECONDS` | `120` | Wall-clock limit for one prediction |
| `INSTALL_ML_DEPS` | `true` | Install torch/torchvision in the image |

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `MODEL_NOT_CONFIGURED` | A checkpoint or `inference.py` is missing | Check `detail` in the status response; the path is listed there |
| `MODEL_LOAD_FAILED` | The checkpoint does not match the architecture, or torch is missing | Read the backend log; check the torch/torchvision version pair |
| `ModuleNotFoundError: No module named 'torch'` | `INSTALL_ML_DEPS=false` | Rebuild with `INSTALL_ML_DEPS=true` |
| `MODEL_BUSY` (503) | Another inference job is running | Retry; raise `INFERENCE_MAX_CONCURRENCY` only if RAM allows |
| `INFERENCE_FAILED` (500) | The model raised during inference | The backend log holds the original exception type in `error.details.reason` |
| `INFERENCE_TIMEOUT` (504) | Inference exceeded the timeout | Raise `INFERENCE_TIMEOUT_SECONDS` or use a smaller image |
| `422` on upload | The file is not a decodable JPEG or PNG | Check the format and the 10 MB limit |
| Slow first prediction | Models load during startup | Expected; the first request after a restart is served by the already-loaded bundle |

---

## 9. What must not change

These remain load-bearing:

1. Do not retrain, fine-tune or re-architect either model.
2. Do not replace the checkpoint weights.
3. Do not modify `backend/inference.py` — it works as transferred. If it ever
   must change, keep the `load_models()` and `predict_image()` signatures and
   the returned dictionary exactly as they are.
4. Do not fabricate predictions — the API must never return a synthetic
   result when the models are unavailable.
5. Do not change the successful prediction JSON shape (`stress` / `growth`)
   without versioning the API and updating the frontend and the database.
6. Do not start persisting uploaded images without agreeing the storage
   provider, access control, retention period and deletion process first.
