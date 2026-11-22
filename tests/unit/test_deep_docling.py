"""Unit tests for DeepDoclingEngine (Docling & RapidOCR)."""

from pathlib import Path

import pymupdf as fitz
import pytest

from omnipdf.core.engines.deep_docling import DeepDoclingEngine
from omnipdf.core.models import ConversionConfig
from tests.fixtures.generate_samples import generate_all_samples


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_deep_docling")
    generate_all_samples(temp_dir)
    return temp_dir


def test_deep_docling_engine_name() -> None:
    engine = DeepDoclingEngine()
    assert engine.engine_name == "docling"


def test_deep_docling_device_detection() -> None:
    engine = DeepDoclingEngine()
    assert engine._device in ("cuda", "cpu")


def test_deep_docling_table_conversion(fixtures_dir: Path, tmp_path: Path) -> None:
    """Test table and multi-column document extraction via Docling."""
    pdf_path = fixtures_dir / "table_multicol.pdf"
    engine = DeepDoclingEngine()
    config = ConversionConfig(output_dir=tmp_path)

    with fitz.open(str(pdf_path)) as doc:
        res = engine.convert_page(doc, page_num=1, config=config)

    assert res.page_num == 1
    assert res.engine_used == "docling"
    assert "CỘT TRÁI" in res.markdown or "TÀI LIỆU CẤU TRÚC" in res.markdown
    assert res.processing_time_ms > 0


def test_deep_docling_scanned_ocr(fixtures_dir: Path, tmp_path: Path) -> None:
    """Test OCR text extraction from scanned document image with zero text layer."""
    pdf_path = fixtures_dir / "scanned_sim.pdf"
    engine = DeepDoclingEngine()
    config = ConversionConfig(output_dir=tmp_path)

    with fitz.open(str(pdf_path)) as doc:
        res = engine.convert_page(doc, page_num=1, config=config)

    assert res.page_num == 1
    assert res.engine_used == "docling"
    # Scanned page must produce non-empty extracted text from OCR
    assert len(res.markdown.strip()) > 50
    # Must contain recognizable words from the rendered scanned receipt
    assert (
        "SCAN" in res.markdown
        or "SKHCN" in res.markdown
        or "VĂN" in res.markdown
        or "THÀNH PH" in res.markdown
    )
