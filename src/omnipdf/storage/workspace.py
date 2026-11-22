"""Workspace and file archive management for conversion jobs."""

import zipfile
from pathlib import Path

import pymupdf as fitz

from omnipdf.core.models import CorruptedPDFError

DEFAULT_WORKSPACES_ROOT = Path("data/workspaces")


def validate_pdf_bytes(content: bytes, filename: str = "document.pdf") -> None:
    """Validate that raw bytes represent a legitimate, uncorrupted PDF document.

    Raises:
        CorruptedPDFError: If magic bytes are wrong or PyMuPDF cannot read the file.
    """
    if len(content) < 10:
        raise CorruptedPDFError(f"Uploaded file '{filename}' is empty or too short.")

    # PDF standard magic number check
    if not content.startswith(b"%PDF-"):
        raise CorruptedPDFError(
            f"Uploaded file '{filename}' is not a valid PDF (invalid magic header)."
        )

    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            if len(doc) == 0:
                raise CorruptedPDFError(f"PDF document '{filename}' contains 0 pages.")
    except Exception as e:
        raise CorruptedPDFError(f"Failed to parse PDF document '{filename}': {e}") from e


def get_job_workspace(job_id: str, base_dir: Path = DEFAULT_WORKSPACES_ROOT) -> Path:
    """Get and ensure dedicated output workspace directory for a job."""
    workspace_dir = base_dir / job_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir


def create_zip_bundle(job_id: str, md_path: Path, output_zip_path: Path | None = None) -> Path:
    """Create a standardized ZIP archive packaging the Markdown file and assets directory."""
    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file does not exist: {md_path}")

    if output_zip_path is None:
        output_zip_path = md_path.parent / f"{md_path.stem}_bundle.zip"

    output_zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add markdown file
        zf.write(md_path, arcname=md_path.name)

        # Add assets folder if present
        assets_dir = md_path.parent / "assets"
        if assets_dir.exists() and assets_dir.is_dir():
            for asset_file in assets_dir.iterdir():
                if asset_file.is_file():
                    zf.write(asset_file, arcname=f"assets/{asset_file.name}")

    return output_zip_path
