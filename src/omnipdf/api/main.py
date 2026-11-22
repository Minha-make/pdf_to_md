"""Main FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnipdf import __version__
from omnipdf.api.routes import router as api_router
from omnipdf.api.routes import set_worker_instance
from omnipdf.api.worker import ConversionWorker, JobEventBroadcaster
from omnipdf.storage.db import DEFAULT_DB_PATH, init_db


def create_app(db_path: Path = DEFAULT_DB_PATH) -> FastAPI:
    """Create and configure FastAPI application with custom DB path for testing."""
    broadcaster = JobEventBroadcaster()
    worker = ConversionWorker(db_path=db_path, broadcaster=broadcaster)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Startup
        await init_db(db_path)
        await worker.start()
        set_worker_instance(worker, broadcaster)
        yield
        # Shutdown
        await worker.stop()

    app = FastAPI(
        title="OmniPDF2MD API",
        version=__version__,
        description="Local Universal PDF-to-Markdown REST API with smart per-page routing and SSE streaming.",
        lifespan=lifespan,
    )

    # CORS configuration for local UI access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
