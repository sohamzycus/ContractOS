FROM python:3.12-slim AS base

WORKDIR /app

# ── System dependencies ──────────────────────────────────
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies (cached layer) ───────────────────
# Copy only dependency metadata first for better layer caching.
# Source code changes won't invalidate this expensive layer.
COPY pyproject.toml README.md ./
COPY src/ src/

# Install production dependencies only (no dev extras)
RUN pip install --no-cache-dir . \
    && pip cache purge 2>/dev/null; true

# ── Pre-download embedding model (baked into image) ──────
# all-MiniLM-L6-v2: ~80MB download, ~90MB on disk, ~250MB in RAM
# This avoids a 30s+ cold-start download on first request.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" \
    && rm -rf /root/.cache/pip

# ── Application files ────────────────────────────────────
# config/ — playbook YAML, NDA checklist, default config
# demo/   — copilot.html, graph.html, index.html, samples/
COPY config/ config/
COPY demo/ demo/

# ── Data directory ───────────────────────────────────────
RUN mkdir -p /data/.contractos

# ── Environment ──────────────────────────────────────────
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PORT=8742

# LLM — set at runtime via docker-compose or docker run -e
ENV ANTHROPIC_API_KEY=""
ENV ANTHROPIC_BASE_URL=""
ENV ANTHROPIC_MODEL=""

# Storage — persistent volume mount point
ENV CONTRACTOS_DB_PATH=/data/.contractos/trustgraph.db

EXPOSE ${PORT}

# ── Health check ─────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:${PORT}/health || exit 1

# ── Entrypoint ───────────────────────────────────────────
# Single worker (SQLite doesn't support concurrent writes across processes).
# Async FastAPI handles concurrency within the single process just fine.
# --timeout-keep-alive 120: keep connections alive for SSE streaming responses.
# --log-level info: structured logging for production.
CMD ["sh", "-c", "python -m uvicorn contractos.api.app:create_app --host 0.0.0.0 --port ${PORT:-8742} --factory --timeout-keep-alive 120 --log-level info"]
