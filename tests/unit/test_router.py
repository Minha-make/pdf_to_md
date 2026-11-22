"""Unit tests for SmartRouter and multi-tier per-page routing."""

from pathlib import Path

import pytest

from omnipdf.core.models import (
    ConversionConfig,
    ConversionMode,
    PageProfile,
    PageType,
)
from omnipdf.core.router import SmartRouter, convert_pdf
from tests.fixtures.generate_samples import generate_all_samples


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_router")
    generate_all_samples(temp_dir)
    return temp_dir


def test_router_select_engine_modes() -> None:
    """Test engine selection across modes and page types."""
    router = SmartRouter()

    p_clean = PageProfile(
        page_num=1,
        width=595,
        height=842,
        character_count=500,
        page_type=PageType.DIGITAL_CLEAN,
        recommended_engine="pymupdf4llm",
    )
    p_complex = PageProfile(
        page_num=2,
        width=595,
        height=842,
        character_count=300,
        page_type=PageType.COMPLEX_LAYOUT,
        recommended_engine="deep_docling",
    )
    p_scan = PageProfile(
        page_num=3,
        width=595,
        height=842,
        character_count=0,
        image_area_ratio=1.0,
        page_type=PageType.SCANNED_IMAGE,
        recommended_engine="deep_docling_ocr",
    )

    # AUTO mode
    cfg_auto = ConversionConfig(mode=ConversionMode.AUTO)
    assert router.select_engine_for_page(p_clean, cfg_auto).engine_name == "pymupdf4llm"
    assert router.select_engine_for_page(p_complex, cfg_auto).engine_name == "docling"
    assert router.select_engine_for_page(p_scan, cfg_auto).engine_name == "docling"

    # AUTO mode with VLM fallback enabled
    cfg_vlm = ConversionConfig(mode=ConversionMode.AUTO, use_vlm=True)
    assert router.select_engine_for_page(p_scan, cfg_vlm).engine_name == "vlm_ollama"

    # Forced FAST mode
    cfg_fast = ConversionConfig(mode=ConversionMode.FAST)
    assert router.select_engine_for_page(p_complex, cfg_fast).engine_name == "pymupdf4llm"
    assert router.select_engine_for_page(p_scan, cfg_fast).engine_name == "pymupdf4llm"

    # Forced DEEP mode
    cfg_deep = ConversionConfig(mode=ConversionMode.DEEP)
    assert router.select_engine_for_page(p_clean, cfg_deep).engine_name == "docling"


def test_router_group_pages() -> None:
    """Test contiguous page grouping to reduce engine context switches."""
    router = SmartRouter()
    profiles = [
        PageProfile(
            page_num=1,
            width=595,
            height=842,
            page_type=PageType.DIGITAL_CLEAN,
            recommended_engine="pymupdf4llm",
        ),
        PageProfile(
            page_num=2,
            width=595,
            height=842,
            page_type=PageType.DIGITAL_CLEAN,
            recommended_engine="pymupdf4llm",
        ),
        PageProfile(
            page_num=3,
            width=595,
            height=842,
            page_type=PageType.COMPLEX_LAYOUT,
            recommended_engine="deep_docling",
        ),
        PageProfile(
            page_num=4,
            width=595,
            height=842,
            page_type=PageType.SCANNED_IMAGE,
            recommended_engine="deep_docling",
        ),
        PageProfile(
            page_num=5,
            width=595,
            height=842,
            page_type=PageType.DIGITAL_CLEAN,
            recommended_engine="pymupdf4llm",
        ),
    ]

    cfg = ConversionConfig(mode=ConversionMode.AUTO)
    groups = router.group_pages_by_engine(profiles, cfg)

    assert len(groups) == 3
    # Group 1: Pages 1, 2 via pymupdf4llm
    assert groups[0][0].engine_name == "pymupdf4llm"
    assert groups[0][1] == [1, 2]
    # Group 2: Pages 3, 4 via docling
    assert groups[1][0].engine_name == "docling"
    assert groups[1][1] == [3, 4]
    # Group 3: Page 5 via pymupdf4llm
    assert groups[2][0].engine_name == "pymupdf4llm"
    assert groups[2][1] == [5]


def test_router_convert_mixed_pdf(fixtures_dir: Path, tmp_path: Path) -> None:
    """Verification Gate 2 test: Converting mixed.pdf routes digital to fast and scan/table to deep."""
    pdf_path = fixtures_dir / "mixed.pdf"
    out_dir = tmp_path / "mixed_out"
    config = ConversionConfig(mode=ConversionMode.AUTO, output_dir=out_dir)

    progress_events: list[tuple[int, int, str]] = []

    def on_progress(curr: int, total: int, engine: str) -> None:
        progress_events.append((curr, total, engine))

    result = convert_pdf(pdf_path, config, on_progress=on_progress)

    assert result.total_pages == 4
    assert len(result.pages) == 4
    assert len(progress_events) == 4

    # Verify per-page engine routing
    assert result.pages[0].engine_used == "pymupdf4llm"  # Page 1: Digital text
    assert result.pages[1].engine_used == "docling"  # Page 2: Table / multi-col
    assert result.pages[2].engine_used == "docling"  # Page 3: Scanned image OCR
    assert result.pages[3].engine_used == "pymupdf4llm"  # Page 4: Text + illustration

    # Verify engines_used list has both
    assert "pymupdf4llm" in result.engines_used
    assert "docling" in result.engines_used

    # Verify output markdown file exists on disk
    assert result.output_path is not None
    assert result.output_path.exists()
    content = result.output_path.read_text(encoding="utf-8")
    assert "VĂN BẢN SỐ" in content
    assert "assets/p0004_img01.png" in content
