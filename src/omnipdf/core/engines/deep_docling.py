"""Tier 2 Deep Layout & OCR Converter Engine using Docling and RapidOCR."""

import logging
import os
import tempfile
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import pymupdf as fitz
from PIL import Image

from omnipdf.core.engines.base import BaseConverterEngine
from omnipdf.core.models import ConversionConfig, PageResult

logger = logging.getLogger(__name__)


class DeepDoclingEngine(BaseConverterEngine):
    """Deep Layout and OCR Engine based on IBM Docling and RapidOCR."""

    def __init__(self, do_ocr: bool = True) -> None:
        self.do_ocr = do_ocr
        self._converter: Any = None
        self._rapid_ocr: Any = None
        self._device = self._detect_device()

    @property
    def engine_name(self) -> str:
        return "docling"

    def _detect_device(self) -> str:
        """Detect CUDA or CPU execution environment."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            # Set bounded threads on CPU for safety
            safe_threads = min(4, os.cpu_count() or 1)
            torch.set_num_threads(safe_threads)
            return "cpu"
        except ImportError:
            return "cpu"

    def _get_converter(self) -> Any:
        """Lazy-initialize the Docling DocumentConverter instance."""
        if self._converter is None:
            try:
                from docling.datamodel.base_models import InputFormat
                from docling.datamodel.pipeline_options import (
                    PdfPipelineOptions,
                    RapidOcrOptions,
                )
                from docling.document_converter import DocumentConverter, PdfFormatOption

                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = self.do_ocr
                pipeline_options.ocr_options = RapidOcrOptions()

                self._converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                    }
                )
            except Exception as e:
                logger.error(f"Failed to initialize Docling converter: {e}")
                raise
        return self._converter

    def _get_rapid_ocr(self) -> Any:
        """Lazy-initialize RapidOCR instance for fast direct scanned page OCR."""
        if self._rapid_ocr is None:
            try:
                from rapidocr import RapidOCR

                self._rapid_ocr = RapidOCR()
            except Exception as e:
                logger.warning(f"RapidOCR direct engine not available: {e}")
                self._rapid_ocr = None
        return self._rapid_ocr

    def _ocr_raster_page(self, page: fitz.Page, dpi: int = 200) -> str:
        """OCR a pure scanned raster page directly with RapidOCR."""
        ocr = self._get_rapid_ocr()
        if ocr is None:
            return ""

        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")

        try:
            out = ocr(img_bytes)
            if hasattr(out, "txts") and out.txts:
                return "\n\n".join(out.txts)
            elif isinstance(out, tuple) and len(out) >= 1 and out[0]:
                lines = [item[1] for item in out[0] if len(item) >= 2]
                return "\n\n".join(lines)
            return ""
        except Exception as e:
            logger.warning(f"Direct RapidOCR failed on page: {e}")
            return ""

    def convert_page(
        self, doc: fitz.Document, page_num: int, config: ConversionConfig
    ) -> PageResult:
        start_time = time.perf_counter()
        page_idx = page_num - 1
        extracted_images: list[Path] = []
        warnings: list[str] = []

        try:
            if page_idx < 0 or page_idx >= len(doc):
                raise IndexError(f"Page number {page_num} out of range (1 to {len(doc)})")

            page = doc[page_idx]
            page_text = page.get_text().strip()

            # If page is pure scanned raster (no text layer), use fast RapidOCR pipeline
            if len(page_text) == 0 and len(page.get_images()) > 0:
                page_md = self._ocr_raster_page(page, dpi=200)
            else:
                # Extract single page into temp PDF and convert with Docling
                with tempfile.TemporaryDirectory() as tmp_dir:
                    temp_pdf_path = Path(tmp_dir) / f"page_{page_num}.pdf"
                    with fitz.open() as temp_doc:
                        temp_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
                        temp_doc.save(str(temp_pdf_path))

                    converter = self._get_converter()
                    conv_res = converter.convert(str(temp_pdf_path))
                    page_md = conv_res.document.export_to_markdown()

            if not isinstance(page_md, str):
                page_md = str(page_md)
            page_md = page_md.strip()

            # Extract image assets if enabled
            if config.extract_images:
                assets_dir = config.output_dir / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)

                image_list = page.get_images()
                img_markdown_blocks: list[str] = []

                for idx, img_info in enumerate(image_list):
                    xref = img_info[0]
                    img_idx = idx + 1
                    asset_filename = f"p{page_num:04d}_img{img_idx:02d}.png"
                    asset_path = assets_dir / asset_filename
                    rel_asset_path = f"assets/{asset_filename}"

                    try:
                        base_image = doc.extract_image(xref)
                        raw_bytes = base_image["image"]

                        with Image.open(BytesIO(raw_bytes)) as pil_img:
                            pil_img.save(str(asset_path), format="PNG")

                        extracted_images.append(asset_path)
                        img_markdown_blocks.append(
                            f"![Page {page_num} Image {img_idx}]({rel_asset_path})"
                        )
                    except Exception as img_err:
                        warn_msg = (
                            f"Failed to extract image {img_idx} on page {page_num}: {img_err}"
                        )
                        logger.warning(warn_msg)
                        warnings.append(warn_msg)

                if img_markdown_blocks and not page_text:
                    # Append image links if not already present
                    page_md = page_md + "\n\n" + "\n\n".join(img_markdown_blocks)

            duration_ms = (time.perf_counter() - start_time) * 1000

            return PageResult(
                page_num=page_num,
                markdown=page_md,
                engine_used=self.engine_name,
                images=extracted_images,
                warnings=warnings,
                processing_time_ms=round(duration_ms, 2),
            )

        except Exception as err:
            duration_ms = (time.perf_counter() - start_time) * 1000
            err_msg = f"Page {page_num} failed in {self.engine_name}: {err}"
            logger.error(err_msg, exc_info=True)
            fallback_md = f"<!-- [OmniPDF Warning: Page {page_num} failed: {err}] -->"

            return PageResult(
                page_num=page_num,
                markdown=fallback_md,
                engine_used=self.engine_name,
                images=[],
                warnings=[err_msg],
                processing_time_ms=round(duration_ms, 2),
            )
