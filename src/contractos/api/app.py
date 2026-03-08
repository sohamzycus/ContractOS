"""FastAPI application factory for ContractOS."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from contractos.api.deps import init_state, shutdown_state
from contractos.api.routes import contracts, health, query, stream, workspace
from contractos.config import ContractOSConfig


def create_app(config: ContractOSConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        import logging

        _log = logging.getLogger("contractos.startup")
        state = init_state(config)

        # Eagerly warm up the embedding model at startup so the first
        # request doesn't pay the 5-10s model-loading cost (critical for
        # Render/Railway free tiers with 30s request timeouts).
        try:
            _log.info("Warming up embedding model...")
            state.embedding_index  # triggers _get_model() in __init__
            _log.info("Embedding model ready.")
        except Exception as e:
            _log.warning("Embedding model warm-up failed (will retry on first request): %s", e)

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
    app.include_router(stream.router)

    # Serve the demo console at /demo
    import os as _os
    from pathlib import Path as _Path

    # Try multiple locations: relative to source tree, or /app/demo in Docker
    _candidates = [
        _Path(__file__).resolve().parent.parent.parent.parent / "demo",  # dev: src/contractos/api/app.py -> project root
        _Path("/app/demo"),  # Docker container
        _Path(_os.getcwd()) / "demo",  # cwd fallback
    ]
    for _demo_dir in _candidates:
        if _demo_dir.is_dir():
            app.mount("/demo", StaticFiles(directory=str(_demo_dir), html=True), name="demo")
            break

    # Serve the presentation at /presentation and provide PPTX download
    _pres_candidates = [
        _Path(__file__).resolve().parent.parent.parent.parent / "presentation",
        _Path("/app/presentation"),
        _Path(_os.getcwd()) / "presentation",
    ]
    for _pres_dir in _pres_candidates:
        if _pres_dir.is_dir():
            @app.get("/presentation/download")
            async def download_pptx():
                """Generate and download the ContractOS Capstone PowerPoint."""
                pptx_path = _pres_dir / "ContractOS_Capstone.pptx"
                if not pptx_path.exists():
                    from presentation.generate_pptx import build_presentation
                    prs = build_presentation()
                    prs.save(str(pptx_path))
                return FileResponse(
                    path=str(pptx_path),
                    media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    filename="ContractOS_Capstone.pptx",
                )

            app.mount("/presentation", StaticFiles(directory=str(_pres_dir), html=True), name="presentation")
            break

    return app
