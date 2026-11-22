"""Tier 3 Local Vision Language Model (VLM) Converter Engine via Ollama API."""

import base64
import logging
import time

import httpx
import pymupdf as fitz

from omnipdf.config import settings
from omnipdf.core.engines.base import BaseConverterEngine
from omnipdf.core.models import ConversionConfig, PageResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional document OCR and transcription assistant. "
    "Transcribe the given document page into clean, standard GitHub Flavored Markdown (GFM). "
    "Preserve all headings, paragraphs, bullet lists, tables, and mathematical expressions. "
    "Use standard LaTeX: $...$ for inline equations and $$...$$ for display equations. "
    "Do NOT include conversational commentary, introductory greetings, or notes. "
    "Output ONLY the transcribed Markdown content."
)


class VLMOllamaEngine(BaseConverterEngine):
    """Local VLM conversion engine connecting to Ollama multimodal models (e.g. qwen2.5vl)."""

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model_name = model_name or settings.ollama_model
        self.timeout = timeout

    @property
    def engine_name(self) -> str:
        return "vlm_ollama"

    def render_page_to_base64(self, page: fitz.Page, dpi: int = 200) -> str:
        """Render a PDF page to base64-encoded PNG string."""
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode("ascii")

    def convert_page(
        self, doc: fitz.Document, page_num: int, config: ConversionConfig
    ) -> PageResult:
        start_time = time.perf_counter()
        page_idx = page_num - 1
        warnings: list[str] = []

        try:
            if page_idx < 0 or page_idx >= len(doc):
                raise IndexError(f"Page number {page_num} out of range (1 to {len(doc)})")

            page = doc[page_idx]

            # 1. Render page to image
            b64_image = self.render_page_to_base64(page, dpi=settings.default_image_dpi)

            # 2. Prepare multimodal request for Ollama
            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": "Transcribe this page into Markdown.",
                        "images": [b64_image],
                    },
                ],
                "stream": False,
            }

            url = f"{self.base_url}/api/chat"
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                page_md = data.get("message", {}).get("content", "").strip()

            duration_ms = (time.perf_counter() - start_time) * 1000

            return PageResult(
                page_num=page_num,
                markdown=page_md,
                engine_used=self.engine_name,
                images=[],
                warnings=warnings,
                processing_time_ms=round(duration_ms, 2),
            )

        except (httpx.ConnectError, httpx.TimeoutException, ConnectionRefusedError) as net_err:
            duration_ms = (time.perf_counter() - start_time) * 1000
            warn_msg = f"VLM Ollama connection failed for page {page_num}: {net_err}"
            logger.warning(warn_msg)
            warnings.append(warn_msg)
            fallback_md = (
                f"<!-- [OmniPDF Warning: Page {page_num} VLM transcription failed: {net_err}] -->"
            )

            return PageResult(
                page_num=page_num,
                markdown=fallback_md,
                engine_used=self.engine_name,
                images=[],
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
