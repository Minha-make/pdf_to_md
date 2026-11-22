"""FastAPI routes for job submission, SSE monitoring, results, and downloads."""

import hashlib
import os
import sys
import urllib.request
import uuid
from pathlib import Path
from typing import Annotated, Any

import pymupdf as fitz
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from omnipdf import __version__
from omnipdf.api.worker import ConversionWorker, JobEventBroadcaster
from omnipdf.config import settings
from omnipdf.core.models import CorruptedPDFError
from omnipdf.storage.db import (
    create_job,
    find_cached_job,
    get_job,
    list_jobs,
)
from omnipdf.storage.workspace import (
    create_zip_bundle,
    get_job_workspace,
    validate_pdf_bytes,
)

router = APIRouter(prefix="/api")

# Worker and Broadcaster references set during app lifespan
_worker: ConversionWorker | None = None
_broadcaster: JobEventBroadcaster | None = None


def set_worker_instance(worker: ConversionWorker, broadcaster: JobEventBroadcaster) -> None:
    """Set global worker references."""
    global _worker, _broadcaster
    _worker = worker
    _broadcaster = broadcaster


def get_worker() -> ConversionWorker:
    if _worker is None:
        raise RuntimeError("Worker has not been initialized.")
    return _worker


def get_broadcaster() -> JobEventBroadcaster:
    if _broadcaster is None:
        raise RuntimeError("Broadcaster has not been initialized.")
    return _broadcaster


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
async def submit_job(
    file: Annotated[UploadFile, File(description="PDF document to convert")],
    mode: Annotated[str, Form()] = "auto",
    password: Annotated[str | None, Form()] = None,
    extract_images: Annotated[bool, Form()] = True,
    ocr_langs: Annotated[str, Form()] = "en,vi",
    use_vlm: Annotated[bool, Form()] = False,
    include_frontmatter: Annotated[bool, Form()] = True,
    force_reconvert: Annotated[bool, Form()] = False,
) -> dict[str, Any]:
    """Upload a PDF file and enqueue for smart conversion, checking Hash Cache first."""
    filename = file.filename or "document.pdf"
    content = await file.read()

    # 1. Validate file format and integrity
    try:
        validate_pdf_bytes(content, filename=filename)
    except CorruptedPDFError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or corrupted PDF file: {err}",
        ) from err

    # 2. Compute SHA-256 for caching
    sha256_hash = hashlib.sha256(content).hexdigest()
    mode_normalized = mode.lower()
    if mode_normalized not in ("auto", "fast", "deep"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conversion mode: '{mode}'. Must be auto, fast, or deep.",
        )

    worker = get_worker()
    db_path = worker.db_path

    # 3. Check Hash Cache if not forcing reconversion
    if not force_reconvert:
        cached_job = await find_cached_job(db_path, sha256_hash, mode_normalized)
        if cached_job:
            cached_job["cached"] = True
            return cached_job

    # 4. Create new job workspace and save original upload
    job_id = str(uuid.uuid4())
    workspace_dir = get_job_workspace(job_id)
    pdf_path = workspace_dir / filename
    pdf_path.write_bytes(content)

    # 5. Extract total pages count
    try:
        with fitz.open(str(pdf_path)) as doc:
            total_pages = len(doc)
    except Exception:
        total_pages = 0

    # 6. Parse configuration
    langs_list = [lang.strip() for lang in ocr_langs.split(",") if lang.strip()]
    config_dict = {
        "mode": mode_normalized,
        "password": password,
        "extract_images": extract_images,
        "ocr_langs": langs_list,
        "use_vlm": use_vlm,
        "include_frontmatter": include_frontmatter,
        "batch_size": settings.default_batch_size,
    }

    job_record = await create_job(
        db_path,
        job_id=job_id,
        filename=filename,
        sha256=sha256_hash,
        mode=mode_normalized,
        config=config_dict,
        total_pages=total_pages,
    )

    # 7. Enqueue job into sequential background worker
    await worker.enqueue_job(
        job_id=job_id,
        input_pdf_path=pdf_path,
        output_dir=workspace_dir,
        config_dict=config_dict,
    )

    job_record["cached"] = False
    return job_record


@router.get("/jobs")
async def list_all_jobs(
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, Any]]:
    """List recent conversion jobs."""
    worker = get_worker()
    return await list_jobs(worker.db_path, limit=limit, offset=offset)


@router.get("/jobs/{job_id}")
async def get_job_details(job_id: str) -> dict[str, Any]:
    """Get metadata and current status for a specific job."""
    worker = get_worker()
    job = await get_job(worker.db_path, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    return job


@router.get("/jobs/{job_id}/events")
async def stream_job_events(job_id: str) -> EventSourceResponse:
    """Stream real-time conversion progress via Server-Sent Events (SSE)."""
    worker = get_worker()
    broadcaster = get_broadcaster()
    job = await get_job(worker.db_path, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    # If job is already in a terminal state, emit single final event
    if job.get("status") in ("completed", "failed", "cancelled"):

        async def terminal_generator() -> Any:
            import json

            yield {
                "event": job.get("status"),
                "data": json.dumps(job),
            }

        return EventSourceResponse(terminal_generator())

    return EventSourceResponse(broadcaster.stream_events(job_id, initial_state=job))


@router.post("/jobs/{job_id}/cancel")
async def cancel_conversion_job(job_id: str) -> dict[str, Any]:
    """Request cancellation for a queued or currently executing conversion job."""
    worker = get_worker()
    job = await get_job(worker.db_path, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.get("status") in ("completed", "failed", "cancelled"):
        return {"job_id": job_id, "status": job.get("status"), "message": "Job already finished."}

    worker.cancel_job(job_id)
    return {"job_id": job_id, "status": "cancelling", "message": "Cancellation request submitted."}


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str) -> dict[str, Any]:
    """Retrieve converted Markdown content and list of extracted image assets."""
    worker = get_worker()
    job = await get_job(worker.db_path, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' has not completed yet (status: {job.get('status')}).",
        )

    md_path_str = job.get("markdown_path")
    if not md_path_str or not Path(md_path_str).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Markdown result file not found on disk.",
        )

    md_path = Path(md_path_str)
    markdown_content = md_path.read_text(encoding="utf-8")

    # Find extracted image assets
    assets: list[str] = []
    assets_dir = md_path.parent / "assets"
    if assets_dir.exists() and assets_dir.is_dir():
        for asset in sorted(assets_dir.iterdir()):
            if asset.is_file():
                assets.append(f"assets/{asset.name}")

    return {
        "job_id": job_id,
        "filename": job.get("filename"),
        "total_pages": job.get("total_pages"),
        "engine_used": job.get("engine_used"),
        "markdown": markdown_content,
        "assets": assets,
        "completed_at": job.get("completed_at"),
    }


@router.get("/jobs/{job_id}/download")
async def download_job_artifact(
    job_id: str,
    format: Annotated[str | None, Query(description="Download format: md | zip")] = None,
) -> FileResponse:
    """Download Markdown file or complete ZIP bundle (including assets)."""
    worker = get_worker()
    job = await get_job(worker.db_path, job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Completed artifact for job '{job_id}' not found.",
        )

    md_path_str = job.get("markdown_path")
    if not md_path_str or not Path(md_path_str).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file missing from storage.",
        )

    md_path = Path(md_path_str)
    assets_dir = md_path.parent / "assets"
    has_assets = assets_dir.exists() and any(assets_dir.iterdir())

    # If ZIP format requested or assets exist and no explicit 'md' requested, package as ZIP
    if format == "zip" or (has_assets and format != "md"):
        zip_path = create_zip_bundle(job_id, md_path)
        return FileResponse(
            path=str(zip_path),
            filename=f"{md_path.stem}.zip",
            media_type="application/zip",
        )

    return FileResponse(
        path=str(md_path),
        filename=md_path.name,
        media_type="text/markdown",
    )


@router.get("/jobs/{job_id}/file")
async def get_job_original_file(job_id: str) -> FileResponse:
    """Serve the original uploaded PDF file for in-browser rendering."""
    worker = get_worker()
    job = await get_job(worker.db_path, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found.",
        )
    filename = job.get("filename", "document.pdf")
    workspace_dir = get_job_workspace(job_id)
    pdf_path = workspace_dir / filename
    if not pdf_path.exists() or not pdf_path.is_file():
        pdf_candidates = list(workspace_dir.glob("*.pdf"))
        if pdf_candidates:
            pdf_path = pdf_candidates[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original PDF file for job '{job_id}' not found.",
            )

    return FileResponse(
        path=str(pdf_path),
        filename=filename,
        media_type="application/pdf",
    )


@router.get("/jobs/{job_id}/assets/{filename}")
async def get_job_asset(job_id: str, filename: str) -> FileResponse:
    """Serve an extracted image asset for a job."""
    safe_filename = Path(filename).name
    workspace_dir = get_job_workspace(job_id)
    asset_path = workspace_dir / "assets" / safe_filename

    if not asset_path.exists() or not asset_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{safe_filename}' not found for job '{job_id}'.",
        )

    return FileResponse(
        path=str(asset_path),
        filename=safe_filename,
        media_type="image/png",
    )


@router.get("/system/status")
async def get_system_status() -> dict[str, Any]:
    """Check hardware resources, compute engine, and Ollama connection status."""
    has_cuda = False
    cuda_name = None
    try:
        import torch

        if torch.cuda.is_available():
            has_cuda = True
            cuda_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    ollama_online = False
    try:
        req = urllib.request.Request(
            f"{settings.ollama_base_url}/api/tags", headers={"User-Agent": "OmniPDF"}
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            if resp.status == 200:
                ollama_online = True
    except Exception:
        ollama_online = False

    worker = get_worker()

    return {
        "version": __version__,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "cpu_count": os.cpu_count() or 1,
        "compute": {
            "device": "cuda" if has_cuda else "cpu",
            "cuda_available": has_cuda,
            "device_name": cuda_name or "CPU",
        },
        "services": {
            "ollama_online": ollama_online,
            "ollama_url": settings.ollama_base_url,
        },
        "queue": {
            "active_job_id": worker._current_job_id,
            "pending_count": worker.queue.qsize(),
        },
    }
