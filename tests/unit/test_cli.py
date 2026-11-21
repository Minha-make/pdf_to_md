"""Unit tests for OmniPDF CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from omnipdf.cli import app
from tests.fixtures.generate_samples import generate_all_samples

runner = CliRunner()


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("fixtures_cli")
    generate_all_samples(temp_dir)
    return temp_dir


def test_cli_doctor() -> None:
    """CLI doctor command returns exit code 0 and prints system info."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "OmniPDF2MD Doctor" in result.stdout
    assert "Python Version" in result.stdout
    assert "PyMuPDF Engine" in result.stdout


def test_cli_convert_clean_vn(fixtures_dir: Path, tmp_path: Path) -> None:
    """CLI convert command converts clean_vn.pdf to valid markdown with assets."""
    pdf_path = fixtures_dir / "clean_vn.pdf"
    out_dir = tmp_path / "cli_out"

    result = runner.invoke(
        app,
        ["convert", str(pdf_path), "-o", str(out_dir), "--mode", "fast"],
    )

    assert result.exit_code == 0
    assert "Conversion Succeeded!" in result.stdout

    md_file = out_dir / "clean_vn.md"
    assert md_file.exists()
    content = md_file.read_text(encoding="utf-8")
    assert "BÁO CÁO KỸ THUẬT" in content
    assert "tiếng Việt" in content


def test_cli_convert_encrypted_pdf(fixtures_dir: Path, tmp_path: Path) -> None:
    """CLI convert rejects encrypted PDF without password, accepts with secret123."""
    pdf_path = fixtures_dir / "encrypted.pdf"
    out_dir = tmp_path / "cli_enc_out"

    # Without password
    result_fail = runner.invoke(
        app,
        ["convert", str(pdf_path), "-o", str(out_dir)],
    )
    assert result_fail.exit_code != 0
    assert "encrypted" in result_fail.stdout.lower()

    # With correct password
    result_ok = runner.invoke(
        app,
        ["convert", str(pdf_path), "-o", str(out_dir), "-p", "secret123"],
    )
    assert result_ok.exit_code == 0
    assert "Conversion Succeeded!" in result_ok.stdout
    md_file = out_dir / "encrypted.md"
    assert md_file.exists()
