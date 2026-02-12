FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for sentence-transformers / FAISS
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifest first for Docker layer caching
COPY pyproject.toml README.md ./

# Copy source code (needed for hatchling build)
COPY src/ src/
COPY config/ config/
COPY demo/ demo/

# Install Python dependencies (production only, no dev extras)
RUN pip install --no-cache-dir .

# Pre-download the sentence-transformers model so cold starts are fast
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Create data directory for SQLite
RUN mkdir -p /data/.contractos

# ── Environment ──────────────────────────────────────────
# These are declared so they can be set at runtime via docker run -e
# or via the hosting platform's environment variable UI.
ENV PYTHONPATH=/app/src
ENV PORT=8742

# LLM configuration — set these at deploy time
ENV ANTHROPIC_API_KEY=""
ENV ANTHROPIC_BASE_URL=""
ENV ANTHROPIC_MODEL=""

# Storage — use /data inside the container
ENV CONTRACTOS_DB_PATH=/data/.contractos/trustgraph.db

EXPOSE ${PORT}

# Health check using curl (respects $PORT at runtime)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run with uvicorn — uses $PORT for platform compatibility (Render, Railway, etc.)
CMD ["sh", "-c", "python -m uvicorn contractos.api.app:create_app --host 0.0.0.0 --port ${PORT:-8742} --factory"]
