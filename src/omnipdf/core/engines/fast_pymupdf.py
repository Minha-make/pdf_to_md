"""Tier 1 Fast Converter Engine using PyMuPDF and PyMuPDF4LLM."""

import logging
import time
from io import BytesIO
from pathlib import Path

import pymupdf as fitz
import pymupdf4llm
from PIL import Image

from omnipdf.core.engines.base import BaseConverterEngine
from omnipdf.core.models import ConversionConfig, PageResult

logger = logging.getLogger(__name__)


class FastPyMuPDFEngine(BaseConverterEngine):
    """Fast PDF-to-Markdown engine based on PyMuPDF and PyMuPDF4LLM."""

    @property
    def engine_name(self) -> str:
        return "pymupdf4llm"

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

            # 1. Convert text layout to Markdown via pymupdf4llm
            page_md = pymupdf4llm.to_markdown(doc, pages=[page_idx], write_images=False)
            if not isinstance(page_md, str):
                page_md = str(page_md)

            # Strip any trailing document-parser headers or empty whitespace
            page_md = page_md.strip()

            # 2. Extract embedded images if enabled
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

                        # Convert and save as standardized PNG using Pillow
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

                if img_markdown_blocks:
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
            error_msg = f"Page {page_num} failed in {self.engine_name}: {err}"
            logger.error(error_msg, exc_info=True)
            fallback_md = f"<!-- [OmniPDF Warning: Page {page_num} failed: {err}] -->"

            return PageResult(
                page_num=page_num,
                markdown=fallback_md,
                engine_used=self.engine_name,
                images=[],
                warnings=[error_msg],
                processing_time_ms=round(duration_ms, 2),
            )
