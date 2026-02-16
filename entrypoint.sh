#!/bin/sh
# ContractOS — Container entrypoint
#
# Starts both FastAPI (main process) and MCP HTTP server (background)
# in the same container to share a single SQLite connection.
#
# Environment variables:
#   MCP_TRANSPORT  — set to "http" to enable MCP HTTP server (default: disabled)
#   MCP_PORT       — MCP HTTP port (default: 8743)
#   PORT           — FastAPI port (default: 8742)

set -e

# Start MCP HTTP server in background if requested
if [ "$MCP_TRANSPORT" = "http" ]; then
    echo "[entrypoint] Starting MCP HTTP server on port ${MCP_PORT:-8743}..."
    python -m contractos.mcp.server --transport http --port "${MCP_PORT:-8743}" &
    MCP_PID=$!
    echo "[entrypoint] MCP server started (PID=$MCP_PID)"
fi

# Start FastAPI as main process
echo "[entrypoint] Starting FastAPI on port ${PORT:-8742}..."
exec python -m uvicorn contractos.api.app:create_app \
    --host 0.0.0.0 \
    --port "${PORT:-8742}" \
    --factory \
    --timeout-keep-alive 120 \
    --log-level info
