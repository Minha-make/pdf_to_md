"""Unit tests for FastPyMuPDFEngine."""

from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image

from omnipdf.core.engines.fast_pymupdf import FastPyMuPDFEngine
from omnipdf.core.models import ConversionConfig
from tests.fixtures.generate_samples import generate_all_samples


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_fast_pymupdf")
    generate_all_samples(temp_dir)
    return temp_dir


def test_convert_clean_vn(fixtures_dir: Path, tmp_path: Path) -> None:
    """Fast engine should cleanly extract Vietnamese digital text."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    engine = FastPyMuPDFEngine()
    config = ConversionConfig(output_dir=tmp_path, extract_images=True)

    with fitz.open(str(pdf_path)) as doc:
        res = engine.convert_page(doc, page_num=1, config=config)

    assert res.page_num == 1
    assert res.engine_used == "pymupdf4llm"
    assert "BÁO CÁO KỸ THUẬT" in res.markdown
    assert "tiếng Việt" in res.markdown
    assert res.processing_time_ms > 0


def test_extract_image_assets(fixtures_dir: Path, tmp_path: Path) -> None:
    """Converting page with images extracts PNG to assets/ and links in Markdown."""
    pdf_path = fixtures_dir / "mixed.pdf"
    engine = FastPyMuPDFEngine()
    config = ConversionConfig(output_dir=tmp_path, extract_images=True)

    with fitz.open(str(pdf_path)) as doc:
        res = engine.convert_page(doc, page_num=4, config=config)

    assert len(res.images) >= 1
    asset_file = res.images[0]
    assert asset_file.exists()
    assert asset_file.name == "p0004_img01.png"
    assert "assets/p0004_img01.png" in res.markdown

    # Verify extracted image is a valid PNG
    with Image.open(asset_file) as img:
        assert img.format == "PNG"


def test_invalid_page_handling(fixtures_dir: Path, tmp_path: Path) -> None:
    """Out-of-bound page should not crash, but emit warning comment."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    engine = FastPyMuPDFEngine()
    config = ConversionConfig(output_dir=tmp_path)

    with fitz.open(str(pdf_path)) as doc:
        res = engine.convert_page(doc, page_num=99, config=config)

    assert "OmniPDF Warning: Page 99 failed" in res.markdown
    assert len(res.warnings) > 0
