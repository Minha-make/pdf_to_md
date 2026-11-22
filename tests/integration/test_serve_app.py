"""Integration tests verifying static file mounting, SPA routing, and API serving."""

from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

from omnipdf.api.main import create_app, find_web_dist


@pytest.fixture
def app_with_dist(tmp_path: Path) -> FastAPI:
    """FastAPI app instance configured with actual web dist (if built)."""
    db_path = tmp_path / "test_serve.db"
    return create_app(db_path=db_path)


@pytest.fixture
def app_without_dist(tmp_path: Path) -> FastAPI:
    """FastAPI app instance configured with non-existent dist directory."""
    db_path = tmp_path / "test_serve_fallback.db"
    fake_dist = tmp_path / "non_existent_dist"
    return create_app(db_path=db_path, dist_dir=fake_dist)


@pytest.fixture
async def client_with_dist(app_with_dist: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with app_with_dist.router.lifespan_context(app_with_dist):
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app_with_dist), base_url="http://test"
        ) as client:
            yield client


@pytest.fixture
async def client_without_dist(
    app_without_dist: FastAPI,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with app_without_dist.router.lifespan_context(app_without_dist):
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app_without_dist), base_url="http://test"
        ) as client:
            yield client


@pytest.mark.asyncio
async def test_serve_spa_with_built_dist(client_with_dist: httpx.AsyncClient) -> None:
    """When web/dist is built, GET / must return index.html and SPA routes must work."""
    dist_path = find_web_dist()
    if not dist_path or not (dist_path / "index.html").exists():
        pytest.skip("web/dist not built yet; skipping live dist verification.")

    # 1. Root route
    res_root = await client_with_dist.get("/")
    assert res_root.status_code == 200
    assert "text/html" in res_root.headers.get("content-type", "")
    assert '<div id="root">' in res_root.text

    # 2. SPA client-side route fallback
    res_spa = await client_with_dist.get("/custom-page")
    assert res_spa.status_code == 200
    assert "text/html" in res_spa.headers.get("content-type", "")
    assert '<div id="root">' in res_spa.text

    # 3. Static asset route
    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        js_files = list(assets_dir.glob("*.js"))
        if js_files:
            asset_filename = js_files[0].name
            res_asset = await client_with_dist.get(f"/assets/{asset_filename}")
            assert res_asset.status_code == 200
            assert len(res_asset.content) > 0

    # 4. API endpoints must NOT be intercepted by SPA fallback
    res_api = await client_with_dist.get("/api/system/status")
    assert res_api.status_code == 200
    assert res_api.json()["version"] is not None

    # 5. Non-existent API route must return 404 JSON, not HTML
    res_404_api = await client_with_dist.get("/api/non_existent_route")
    assert res_404_api.status_code == 404
    assert "application/json" in res_404_api.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_serve_fallback_when_no_dist(client_without_dist: httpx.AsyncClient) -> None:
    """When web/dist does not exist, GET / returns a friendly diagnostic HTML landing."""
    res = await client_without_dist.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "OmniPDF2MD API Server" in res.text
    assert "/docs" in res.text
