"""FastAPI application factory for ContractOS."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from contractos.api.deps import init_state, shutdown_state
from contractos.api.routes import contracts, health, query, workspace
from contractos.config import ContractOSConfig


def create_app(config: ContractOSConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        init_state(config)
        yield
        shutdown_state()

    app = FastAPI(
        title="ContractOS",
        description="Contract Intelligence API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow the demo console and local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(contracts.router)
    app.include_router(query.router)
    app.include_router(workspace.router)

    # Serve the demo console at /demo
    import importlib.resources as _res
    from pathlib import Path as _Path

    _demo_dir = _Path(__file__).resolve().parent.parent.parent.parent / "demo"
    if _demo_dir.is_dir():
        app.mount("/demo", StaticFiles(directory=str(_demo_dir), html=True), name="demo")

    return app
