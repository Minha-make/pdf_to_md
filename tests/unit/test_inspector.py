"""Unit tests for pre-flight page inspector and classifier."""

from pathlib import Path

import pytest

from omnipdf.core.inspector import inspect_pdf
from omnipdf.core.models import EncryptedPDFError, PageType
from tests.fixtures.generate_samples import generate_all_samples


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_inspector")
    generate_all_samples(temp_dir)
    return temp_dir


def test_inspect_clean_vn(fixtures_dir: Path) -> None:
    """clean_vn.pdf must be classified as DIGITAL_CLEAN."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    profiles = inspect_pdf(pdf_path)

    assert len(profiles) == 1
    p = profiles[0]
    assert p.page_type == PageType.DIGITAL_CLEAN
    assert p.recommended_engine == "pymupdf4llm"
    assert p.character_count >= 100
    assert p.column_count == 1
    assert p.has_table is False


def test_inspect_table_multicol(fixtures_dir: Path) -> None:
    """table_multicol.pdf must be classified as COMPLEX_LAYOUT."""
    pdf_path = fixtures_dir / "table_multicol.pdf"
    profiles = inspect_pdf(pdf_path)

    assert len(profiles) == 1
    p = profiles[0]
    assert p.page_type == PageType.COMPLEX_LAYOUT
    assert p.recommended_engine == "deep_docling"
    assert p.has_table is True or p.column_count >= 2


def test_inspect_scanned_sim(fixtures_dir: Path) -> None:
    """scanned_sim.pdf must be classified as SCANNED_IMAGE."""
    pdf_path = fixtures_dir / "scanned_sim.pdf"
    profiles = inspect_pdf(pdf_path)

    assert len(profiles) == 1
    p = profiles[0]
    assert p.page_type == PageType.SCANNED_IMAGE
    assert p.recommended_engine == "deep_docling_ocr"
    assert p.character_count < 50
    assert p.image_area_ratio > 0.50


def test_inspect_mixed_document(fixtures_dir: Path) -> None:
    """mixed.pdf must correctly classify each of the 4 mixed pages."""
    pdf_path = fixtures_dir / "mixed.pdf"
    profiles = inspect_pdf(pdf_path)

    assert len(profiles) == 4
    types = [p.page_type for p in profiles]
    assert types == [
        PageType.DIGITAL_CLEAN,
        PageType.COMPLEX_LAYOUT,
        PageType.SCANNED_IMAGE,
        PageType.DIGITAL_CLEAN,
    ]


def test_inspect_encrypted_pdf_handling(fixtures_dir: Path) -> None:
    """encrypted.pdf must raise EncryptedPDFError without password, and succeed with secret123."""
    pdf_path = fixtures_dir / "encrypted.pdf"

    # Without password
    with pytest.raises(EncryptedPDFError):
        inspect_pdf(pdf_path)

    # With wrong password
    with pytest.raises(EncryptedPDFError):
        inspect_pdf(pdf_path, password="wrongpassword")

    # With correct password
    profiles = inspect_pdf(pdf_path, password="secret123")
    assert len(profiles) == 1
    assert profiles[0].page_type == PageType.DIGITAL_CLEAN


def test_inspect_nonexistent_file() -> None:
    """Attempting to inspect nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        inspect_pdf(Path("does_not_exist_xyz.pdf"))
