"""Unit tests for Markdown post-processing pipeline."""

from omnipdf.core.models import ConversionConfig, PageResult
from omnipdf.core.postprocess import (
    deduplicate_headers_footers,
    generate_frontmatter,
    normalize_latex,
    normalize_whitespace,
    postprocess_document,
)


def test_normalize_latex() -> None:
    """Test standardization of inline and block LaTeX expressions."""
    input_text = "Equation inline \\(E = mc^2\\) and block:\n\\[\\sum_{i=1}^n x_i = S\\]"
    result = normalize_latex(input_text)
    assert "$E = mc^2$" in result
    assert "$$\n\\sum_{i=1}^n x_i = S\n$$" in result


def test_normalize_whitespace() -> None:
    """Test collapsing of multiple consecutive blank lines."""
    input_text = "Line 1   \r\n\r\n\r\n\r\nLine 2\n\n\n\nLine 3"
    result = normalize_whitespace(input_text)
    assert result == "Line 1\n\nLine 2\n\nLine 3"


def test_deduplicate_headers_footers() -> None:
    """Repetitive header appearing across > 60% of pages is stripped."""
    pages = [
        "Company Header — Confidential\nContent of page 1\nPage 1",
        "Company Header — Confidential\nContent of page 2\nPage 2",
        "Company Header — Confidential\nContent of page 3\nPage 3",
        "Different Header\nContent of page 4\nFooter 4",
    ]
    cleaned = deduplicate_headers_footers(pages)
    # The common top line and bottom page numbers should be stripped from the 3 pages
    assert "Company Header — Confidential" not in cleaned[0]
    assert "Company Header — Confidential" not in cleaned[1]
    assert "Company Header — Confidential" not in cleaned[2]
    assert "Content of page 1" in cleaned[0]


def test_postprocess_document_with_frontmatter() -> None:
    """Test assembly of full document with frontmatter."""
    p1 = PageResult(page_num=1, markdown="# Title\nHello world", engine_used="pymupdf4llm")
    p2 = PageResult(page_num=2, markdown="## Section 2\nMore text", engine_used="pymupdf4llm")

    config = ConversionConfig(include_frontmatter=True)
    doc = postprocess_document([p1, p2], config, source_filename="test.pdf", sha256_hash="123456")

    assert doc.startswith("---\n")
    assert "source_file: test.pdf" in doc
    assert "sha256: '123456'" in doc or 'sha256: "123456"' in doc or "sha256: 123456" in doc
    assert "total_pages: 2" in doc
    assert "Page Break" in doc
    assert "# Title" in doc
    assert "## Section 2" in doc


def test_generate_frontmatter() -> None:
    """Test YAML frontmatter generation."""
    meta = {"source": "demo.pdf", "pages": 5}
    fm = generate_frontmatter(meta)
    assert fm.startswith("---\n")
    assert "source: demo.pdf" in fm
    assert "pages: 5" in fm
    assert fm.endswith("---\n\n")
