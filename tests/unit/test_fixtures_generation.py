"""Unit test verifying the integrity of synthetic PDF test fixtures."""

import unicodedata
from pathlib import Path

import pymupdf as fitz
import pytest

from tests.fixtures.generate_samples import generate_all_samples


def _get_clean_text(page: fitz.Page) -> str:
    """Extract page text and normalize Unicode whitespace (e.g. non-breaking spaces)."""
    return unicodedata.normalize("NFKC", page.get_text())


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate sample fixtures in a dedicated test directory."""
    temp_dir = tmp_path_factory.mktemp("fixtures")
    generate_all_samples(temp_dir)
    return temp_dir


def test_clean_vn_content(fixtures_dir: Path) -> None:
    """Verify clean_vn.pdf contains valid Vietnamese text with diacritics."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    assert pdf_path.exists(), "clean_vn.pdf was not generated"

    with fitz.open(str(pdf_path)) as doc:
        assert len(doc) == 1
        page = doc[0]
        text = _get_clean_text(page)

        # Check for Vietnamese keywords and full diacritics
        assert "BÁO CÁO KỸ THUẬT DỰ ÁN OMNIPDF2MD" in text
        assert "tiếng Việt" in text
        assert "a á à ả ã ạ" in text
        assert "u ú ù ủ ũ ụ ư ứ ừ sử ữ ự" in text


def test_table_multicol_content(fixtures_dir: Path) -> None:
    """Verify table_multicol.pdf contains multiple columns and table contents."""
    pdf_path = fixtures_dir / "table_multicol.pdf"
    assert pdf_path.exists(), "table_multicol.pdf was not generated"

    with fitz.open(str(pdf_path)) as doc:
        assert len(doc) == 1
        page = doc[0]
        text = _get_clean_text(page)

        assert "CỘT TRÁI" in text
        assert "CỘT PHẢI" in text
        assert "PyMuPDF4LLM" in text
        assert "Docling TableFormer" in text


def test_scanned_sim_zero_text(fixtures_dir: Path) -> None:
    """Verify scanned_sim.pdf is pure raster with zero extracted digital text."""
    pdf_path = fixtures_dir / "scanned_sim.pdf"
    assert pdf_path.exists(), "scanned_sim.pdf was not generated"

    with fitz.open(str(pdf_path)) as doc:
        assert len(doc) == 1
        page = doc[0]
        # Text layer must be empty (0 characters)
        assert page.get_text().strip() == ""
        # Must contain at least one raster image
        images = page.get_images()
        assert len(images) >= 1


def test_mixed_pages_structure(fixtures_dir: Path) -> None:
    """Verify mixed.pdf has 4 pages matching the planned layout types."""
    pdf_path = fixtures_dir / "mixed.pdf"
    assert pdf_path.exists(), "mixed.pdf was not generated"

    with fitz.open(str(pdf_path)) as doc:
        assert len(doc) == 4

        # Page 1: Digital text
        assert "VĂN BẢN SỐ" in _get_clean_text(doc[0])

        # Page 2: Complex table layout
        assert "CẤU TRÚC PHỨC TẠP" in _get_clean_text(doc[1])

        # Page 3: Pure raster scan
        assert doc[2].get_text().strip() == ""
        assert len(doc[2].get_images()) >= 1

        # Page 4: Text + embedded illustration
        assert "HÌNH ẢNH MINH HỌA" in _get_clean_text(doc[3])
        assert len(doc[3].get_images()) >= 1


def test_encrypted_pdf_password_protection(fixtures_dir: Path) -> None:
    """Verify encrypted.pdf requires password 'secret123' and rejects invalid attempts."""
    pdf_path = fixtures_dir / "encrypted.pdf"
    assert pdf_path.exists(), "encrypted.pdf was not generated"

    with fitz.open(str(pdf_path)) as doc:
        assert doc.is_encrypted, "PDF should be flagged as encrypted"
        # Try wrong password
        assert not doc.authenticate("wrongpass"), "Should fail with wrong password"
        # Try correct password
        assert doc.authenticate("secret123"), "Should authenticate with secret123"
        # Verify decrypted content
        text = _get_clean_text(doc[0])
        assert "TÀI LIỆU BẢO MẬT" in text
