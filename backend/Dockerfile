# ---------------------------------------------------------------------------
# Backend container image for Planet Health.
#
# The image starts and serves every endpoint even when the model checkpoints
# are absent — the prediction endpoint then answers with HTTP 503.
#
# Build arguments
# ---------------
# INSTALL_ML_DEPS   true  -> also install torch / torchvision (CPU build)
#                   false -> core API only (much smaller and faster to build)
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# --- Dependencies ----------------------------------------------------------
COPY requirements.txt requirements-ml.txt ./

ARG INSTALL_ML_DEPS=true
ARG TORCH_CPU_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

RUN if [ "$INSTALL_ML_DEPS" = "true" ]; then \
        echo "Installing PyTorch CPU runtime..." && \
        pip install --no-cache-dir --index-url "${TORCH_CPU_INDEX_URL}" \
            "torch==2.9.1" "torchvision==0.24.1" ; \
    else \
        echo "Skipping PyTorch runtime (INSTALL_ML_DEPS=false)." ; \
    fi

# --- Application -----------------------------------------------------------
COPY . .

# The model checkpoint directories are prepared here. The .pth files are added
# in Phase 2 (see INSTRUCTIONS_TO_CHRIS.md) and are intentionally not part of
# this repository.
RUN mkdir -p models/growth models/stress

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
