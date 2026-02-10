"""Health check and configuration endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from contractos.api.deps import AppState, get_state

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Service health status."""

    status: str
    service: str
    version: str = "0.1.0"


class ConfigResponse(BaseModel):
    """Current configuration (non-sensitive)."""

    llm_provider: str
    llm_model: str
    storage_backend: str
    extraction_pipeline: list[str]
    server_host: str
    server_port: int
    version: str = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(status="ok", service="contractos")


@router.get("/config", response_model=ConfigResponse)
async def get_config(
    state: Annotated[AppState, Depends(get_state)],
) -> ConfigResponse:
    """Return current configuration (non-sensitive — no API keys)."""
    cfg = state.config
    return ConfigResponse(
        llm_provider=cfg.llm.provider,
        llm_model=cfg.llm.model,
        storage_backend=cfg.storage.backend,
        extraction_pipeline=cfg.extraction.pipeline,
        server_host=cfg.server.host,
        server_port=cfg.server.port,
    )
