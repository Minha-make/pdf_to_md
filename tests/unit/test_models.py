"""Unit tests for OmniPDF data models and exceptions."""

from pathlib import Path

import pytest

from omnipdf.core.models import (
    ConversionConfig,
    ConversionMode,
    ConversionResult,
    EncryptedPDFError,
    OmniPDFError,
    PageProfile,
    PageResult,
    PageType,
)


def test_page_profile_validation() -> None:
    """Test valid construction and validation of PageProfile."""
    profile = PageProfile(
        page_num=1,
        width=595.0,
        height=842.0,
        character_count=450,
        image_count=0,
        image_area_ratio=0.0,
        column_count=1,
        has_table=False,
        garbled_char_count=0,
        page_type=PageType.DIGITAL_CLEAN,
        recommended_engine="pymupdf4llm",
    )
    assert profile.page_num == 1
    assert profile.page_type == PageType.DIGITAL_CLEAN
    assert profile.recommended_engine == "pymupdf4llm"


def test_conversion_config_defaults() -> None:
    """Test ConversionConfig default values."""
    config = ConversionConfig()
    assert config.mode == ConversionMode.AUTO
    assert config.password is None
    assert config.extract_images is True
    assert config.output_dir == Path("output")
    assert config.ocr_langs == ["en", "vi"]
    assert config.include_frontmatter is True
    assert config.batch_size == 15


def test_conversion_result_aggregation() -> None:
    """Test PageResult and ConversionResult models."""
    p1 = PageResult(
        page_num=1,
        markdown="# Page 1 Content",
        engine_used="pymupdf4llm",
        processing_time_ms=45.2,
    )
    res = ConversionResult(
        source_file=Path("test.pdf"),
        sha256="abc123def456",
        total_pages=1,
        pages=[p1],
        full_markdown="# Page 1 Content",
        engines_used=["pymupdf4llm"],
        total_time_ms=50.0,
    )
    assert res.total_pages == 1
    assert len(res.pages) == 1
    assert res.engines_used == ["pymupdf4llm"]


def test_exceptions_hierarchy() -> None:
    """Test that domain exceptions inherit properly from OmniPDFError."""
    assert issubclass(EncryptedPDFError, OmniPDFError)
    with pytest.raises(EncryptedPDFError):
        raise EncryptedPDFError("Encrypted!")
