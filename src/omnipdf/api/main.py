"""Main FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from omnipdf import __version__
from omnipdf.api.routes import router as api_router
from omnipdf.api.routes import set_worker_instance
from omnipdf.api.worker import ConversionWorker, JobEventBroadcaster
from omnipdf.storage.db import DEFAULT_DB_PATH, init_db


def find_web_dist() -> Path | None:
    """Find the compiled web frontend dist directory if it exists."""
    # 1. Check relative to repository root
    repo_dist = Path(__file__).resolve().parent.parent.parent.parent / "web" / "dist"
    if repo_dist.exists() and (repo_dist / "index.html").exists():
        return repo_dist

    # 2. Check bundled package directory
    pkg_dist = Path(__file__).resolve().parent.parent / "web_dist"
    if pkg_dist.exists() and (pkg_dist / "index.html").exists():
        return pkg_dist

    return None


def create_app(
    db_path: Path = DEFAULT_DB_PATH,
    dist_dir: Path | None = None,
) -> FastAPI:
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

    # API routes
    app.include_router(api_router)

    # Web Studio Static Files & SPA mounting
    active_dist = dist_dir if dist_dir is not None else find_web_dist()

    if active_dist and active_dist.exists() and (active_dist / "index.html").exists():
        assets_dir = active_dist / "assets"
        if assets_dir.exists() and assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="web_assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            # Do not intercept API routes, OpenAPI docs, or schema
            if (
                full_path.startswith("api")
                or full_path.startswith("docs")
                or full_path.startswith("openapi.json")
            ):
                raise HTTPException(status_code=404, detail="Not Found")

            target_file = active_dist / full_path
            if full_path and target_file.is_file():
                return FileResponse(path=str(target_file))

            return FileResponse(path=str(active_dist / "index.html"))

    else:

        @app.get("/", include_in_schema=False)
        async def fallback_landing() -> HTMLResponse:
            return HTMLResponse(
                "<html><head><title>OmniPDF2MD</title></head>"
                "<body style='font-family:system-ui,sans-serif;text-align:center;padding:60px;background:#0f172a;color:#f8fafc;'>"
                "<h1 style='color:#818cf8;'>OmniPDF2MD API Server</h1>"
                "<p style='color:#94a3b8;'>Backend API is active and ready.</p>"
                "<p>API Docs: <a href='/docs' style='color:#a5b4fc;'>/docs</a></p>"
                "<p style='margin-top:30px;font-size:13px;color:#64748b;'>"
                "To build the Web Studio UI, run: <code>cd web && npm install && npm run build</code>"
                "</p>"
                "</body></html>"
            )

    return app


app = create_app()
