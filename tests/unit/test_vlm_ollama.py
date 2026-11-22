"""Unit tests for VLMOllamaEngine with mock HTTP responses."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pymupdf as fitz
import pytest

from omnipdf.core.engines.vlm_ollama import VLMOllamaEngine
from omnipdf.core.models import ConversionConfig
from tests.fixtures.generate_samples import generate_all_samples


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_vlm")
    generate_all_samples(temp_dir)
    return temp_dir


def test_vlm_engine_name() -> None:
    engine = VLMOllamaEngine()
    assert engine.engine_name == "vlm_ollama"


def test_vlm_successful_transcription(fixtures_dir: Path, tmp_path: Path) -> None:
    """Test successful VLM response via mocked httpx post."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    engine = VLMOllamaEngine()
    config = ConversionConfig(output_dir=tmp_path)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "# Transcribed Content\nMocked VLM response."}
    }

    with patch.object(httpx.Client, "post", return_value=mock_response):
        with fitz.open(str(pdf_path)) as doc:
            res = engine.convert_page(doc, page_num=1, config=config)

    assert res.page_num == 1
    assert res.engine_used == "vlm_ollama"
    assert "# Transcribed Content" in res.markdown
    assert "Mocked VLM response." in res.markdown
    assert len(res.warnings) == 0


def test_vlm_connection_error_handling(fixtures_dir: Path, tmp_path: Path) -> None:
    """Test graceful handling when Ollama service is unreachable."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    engine = VLMOllamaEngine()
    config = ConversionConfig(output_dir=tmp_path)

    with patch.object(httpx.Client, "post", side_effect=httpx.ConnectError("Connection refused")):
        with fitz.open(str(pdf_path)) as doc:
            res = engine.convert_page(doc, page_num=1, config=config)

    assert res.page_num == 1
    assert res.engine_used == "vlm_ollama"
    assert "OmniPDF Warning: Page 1 VLM transcription failed" in res.markdown
    assert len(res.warnings) >= 1


def test_vlm_invalid_page_index(fixtures_dir: Path, tmp_path: Path) -> None:
    """Test that out-of-range page number returns warning result without crashing."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    engine = VLMOllamaEngine()
    config = ConversionConfig(output_dir=tmp_path)

    with fitz.open(str(pdf_path)) as doc:
        res = engine.convert_page(doc, page_num=999, config=config)

    assert "OmniPDF Warning: Page 999 failed" in res.markdown
    assert len(res.warnings) > 0
