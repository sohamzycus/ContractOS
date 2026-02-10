"""FastAPI application factory for ContractOS."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from contractos.api.deps import init_state, shutdown_state
from contractos.api.routes import contracts, health, query
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
    app.include_router(health.router)
    app.include_router(contracts.router)
    app.include_router(query.router)
    return app
