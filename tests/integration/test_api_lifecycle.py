"""Integration test suite verifying the complete API and job conversion lifecycle."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from omnipdf.api.main import create_app
from tests.fixtures.generate_samples import generate_all_samples


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_api")
    generate_all_samples(temp_dir)
    return temp_dir


@pytest.fixture
def app_instance(tmp_path: Path) -> FastAPI:
    db_path = tmp_path / "test_omnipdf.db"
    return create_app(db_path=db_path)


@pytest.fixture
async def api_client(app_instance: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Test client running inside app's lifespan context."""
    async with app_instance.router.lifespan_context(app_instance):
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app_instance), base_url="http://test"
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_fake_pdf_rejection(api_client: httpx.AsyncClient) -> None:
    """Uploading a non-PDF file disguised as a .pdf must return HTTP 400 Bad Request."""
    files = {
        "file": (
            "fake_document.pdf",
            b"This is plain text pretending to be a PDF file.",
            "application/pdf",
        )
    }
    response = await api_client.post("/api/jobs", files=files)

    assert response.status_code == 400
    assert "invalid or corrupted" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_full_job_lifecycle_and_caching(
    api_client: httpx.AsyncClient, fixtures_dir: Path
) -> None:
    """Test full workflow: upload -> poll status -> fetch result -> download -> hash cache hit."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    pdf_bytes = pdf_path.read_bytes()

    # 1. Submit conversion job
    files = {"file": ("clean_vn.pdf", pdf_bytes, "application/pdf")}
    data = {"mode": "fast", "extract_images": "true"}
    res_post = await api_client.post("/api/jobs", files=files, data=data)

    assert res_post.status_code == 201
    job_data = res_post.json()
    job_id = job_data["id"]
    assert job_data["cached"] is False
    assert job_data["status"] in ("pending", "processing")

    # 2. Poll until completed (timeout after 15s)
    completed = False
    for _ in range(30):
        await asyncio.sleep(0.5)
        res_get = await api_client.get(f"/api/jobs/{job_id}")
        assert res_get.status_code == 200
        current_status = res_get.json()["status"]
        if current_status == "completed":
            completed = True
            break
        elif current_status == "failed":
            pytest.fail(f"Job failed: {res_get.json().get('error_message')}")

    assert completed, "Job did not complete within expected timeout."

    # 3. Retrieve result
    res_result = await api_client.get(f"/api/jobs/{job_id}/result")
    assert res_result.status_code == 200
    result_json = res_result.json()
    assert "BÁO CÁO KỸ THUẬT" in result_json["markdown"]
    assert "tiếng Việt" in result_json["markdown"]

    # 4. Download Markdown and ZIP
    res_dl_md = await api_client.get(f"/api/jobs/{job_id}/download?format=md")
    assert res_dl_md.status_code == 200
    assert "text/markdown" in res_dl_md.headers.get("content-type", "")

    res_dl_zip = await api_client.get(f"/api/jobs/{job_id}/download?format=zip")
    assert res_dl_zip.status_code == 200
    assert "application/zip" in res_dl_zip.headers.get("content-type", "")

    # 5. Verify Hash Cache hit on identical upload without force_reconvert
    files_cached = {"file": ("clean_vn.pdf", pdf_bytes, "application/pdf")}
    data_cached = {"mode": "fast"}
    res_cache = await api_client.post("/api/jobs", files=files_cached, data=data_cached)

    assert res_cache.status_code == 201
    cache_data = res_cache.json()
    assert cache_data["id"] == job_id
    assert cache_data["cached"] is True
    assert cache_data["status"] == "completed"


@pytest.mark.asyncio
async def test_job_cancellation(api_client: httpx.AsyncClient, fixtures_dir: Path) -> None:
    """Test cancelling an enqueued or running job."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    pdf_bytes = pdf_path.read_bytes()

    files = {"file": ("clean_vn.pdf", pdf_bytes, "application/pdf")}
    data = {"mode": "fast", "force_reconvert": "true"}
    res_post = await api_client.post("/api/jobs", files=files, data=data)
    assert res_post.status_code == 201
    job_id = res_post.json()["id"]

    # Request cancellation
    res_cancel = await api_client.post(f"/api/jobs/{job_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] in ("cancelling", "cancelled", "completed")


@pytest.mark.asyncio
async def test_system_status_endpoint(api_client: httpx.AsyncClient) -> None:
    """Test GET /api/system/status returns expected hardware and service keys."""
    res = await api_client.get("/api/system/status")
    assert res.status_code == 200
    status_data = res.json()
    assert "version" in status_data
    assert "python_version" in status_data
    assert "compute" in status_data
    assert "services" in status_data
    assert "queue" in status_data
