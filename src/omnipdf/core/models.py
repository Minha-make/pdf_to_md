"""Standard data contracts and Pydantic models for OmniPDF2MD."""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class PageType(StrEnum):
    """Classification of an individual PDF page."""

    DIGITAL_CLEAN = "DIGITAL_CLEAN"
    COMPLEX_LAYOUT = "COMPLEX_LAYOUT"
    SCANNED_IMAGE = "SCANNED_IMAGE"
    GARBLED_ENCODING = "GARBLED_ENCODING"


class ConversionMode(StrEnum):
    """Execution mode for PDF conversion."""

    AUTO = "auto"
    FAST = "fast"
    DEEP = "deep"


class PageProfile(BaseModel):
    """Detailed structural profile of a single PDF page."""

    page_num: int = Field(..., description="1-based page index")
    width: float = Field(..., description="Page width in points")
    height: float = Field(..., description="Page height in points")
    character_count: int = Field(default=0, description="Total non-whitespace characters")
    image_count: int = Field(default=0, description="Number of embedded raster images")
    image_area_ratio: float = Field(
        default=0.0, description="Proportion of page area covered by images (0.0 to 1.0)"
    )
    column_count: int = Field(default=1, description="Detected number of text columns")
    has_table: bool = Field(default=False, description="Whether table/grid structures are detected")
    garbled_char_count: int = Field(
        default=0, description="Count of replacement or unmapped Unicode characters"
    )
    page_type: PageType = Field(..., description="Classified page category")
    recommended_engine: str = Field(..., description="Engine recommended for processing")


class ConversionConfig(BaseModel):
    """Runtime configuration parameters for a conversion task."""

    mode: ConversionMode = Field(default=ConversionMode.AUTO, description="Conversion mode")
    password: str | None = Field(default=None, description="Password for encrypted PDFs")
    extract_images: bool = Field(default=True, description="Whether to extract images to disk")
    output_dir: Path = Field(default=Path("output"), description="Target directory for output")
    ocr_langs: list[str] = Field(default_factory=lambda: ["en", "vi"], description="OCR languages")
    use_vlm: bool = Field(
        default=False, description="Enable local VLM fallback for difficult pages"
    )
    include_frontmatter: bool = Field(
        default=True, description="Prepend YAML metadata frontmatter to Markdown"
    )
    batch_size: int = Field(
        default=15, description="Number of pages per processing chunk for memory safety"
    )


class PageResult(BaseModel):
    """Conversion output for a single page."""

    page_num: int = Field(..., description="1-based page index")
    markdown: str = Field(..., description="Converted Markdown content for this page")
    engine_used: str = Field(..., description="Name of the engine that handled this page")
    images: list[Path] = Field(default_factory=list, description="Extracted image asset paths")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings or notices")
    processing_time_ms: float = Field(
        default=0.0, description="Processing duration in milliseconds"
    )


class ConversionResult(BaseModel):
    """Complete aggregated conversion result for a PDF document."""

    source_file: Path = Field(..., description="Path to original PDF file")
    sha256: str = Field(..., description="SHA-256 hash of the input document")
    total_pages: int = Field(..., description="Total pages processed")
    pages: list[PageResult] = Field(default_factory=list, description="Per-page conversion results")
    full_markdown: str = Field(..., description="Unified final Markdown document")
    output_path: Path | None = Field(default=None, description="Path where Markdown was saved")
    engines_used: list[str] = Field(
        default_factory=list, description="All engines that contributed"
    )
    total_time_ms: float = Field(
        default=0.0, description="Total execution duration in milliseconds"
    )


# Domain Exceptions


class OmniPDFError(Exception):
    """Base exception for all OmniPDF errors."""

    pass


class EncryptedPDFError(OmniPDFError):
    """Raised when a PDF is encrypted and cannot be opened with the provided credentials."""

    pass


class CorruptedPDFError(OmniPDFError):
    """Raised when a PDF file is malformed or corrupted."""

    pass


class EngineError(OmniPDFError):
    """Raised when a conversion engine fails unexpectedly."""

    pass
