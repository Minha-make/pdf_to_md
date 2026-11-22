"""Smart per-page router and multi-tier conversion orchestrator."""

import gc
import hashlib
import logging
import time
from collections.abc import Callable
from pathlib import Path

import pymupdf as fitz

from omnipdf.core.engines.base import BaseConverterEngine
from omnipdf.core.engines.deep_docling import DeepDoclingEngine
from omnipdf.core.engines.fast_pymupdf import FastPyMuPDFEngine
from omnipdf.core.engines.vlm_ollama import VLMOllamaEngine
from omnipdf.core.inspector import inspect_pdf
from omnipdf.core.models import (
    ConversionConfig,
    ConversionMode,
    ConversionResult,
    EncryptedPDFError,
    PageProfile,
    PageResult,
    PageType,
)
from omnipdf.core.postprocess import postprocess_document

logger = logging.getLogger(__name__)


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class SmartRouter:
    """Orchestrates per-page inspection, multi-tier engine selection, and chunked execution."""

    def __init__(self) -> None:
        self.fast_engine = FastPyMuPDFEngine()
        self.deep_engine = DeepDoclingEngine(do_ocr=True)
        self.vlm_engine = VLMOllamaEngine()

    def select_engine_for_page(
        self, profile: PageProfile, config: ConversionConfig
    ) -> BaseConverterEngine:
        """Determine the most appropriate converter engine for an individual page."""
        # 1. User forced FAST mode
        if config.mode == ConversionMode.FAST:
            return self.fast_engine

        # 2. User forced DEEP mode
        if config.mode == ConversionMode.DEEP:
            if config.use_vlm:
                return self.vlm_engine
            return self.deep_engine

        # 3. AUTO Mode: Smart per-page routing
        if profile.page_type == PageType.DIGITAL_CLEAN:
            return self.fast_engine

        if profile.page_type == PageType.COMPLEX_LAYOUT:
            return self.deep_engine

        if profile.page_type in (PageType.SCANNED_IMAGE, PageType.GARBLED_ENCODING):
            if config.use_vlm:
                return self.vlm_engine
            return self.deep_engine

        # Default fallback
        return self.fast_engine

    def group_pages_by_engine(
        self,
        profiles: list[PageProfile],
        config: ConversionConfig,
    ) -> list[tuple[BaseConverterEngine, list[int]]]:
        """Group consecutive pages targeted for the same engine to minimize context switching."""
        groups: list[tuple[BaseConverterEngine, list[int]]] = []

        current_engine: BaseConverterEngine | None = None
        current_page_nums: list[int] = []

        for p in profiles:
            engine = self.select_engine_for_page(p, config)
            if current_engine is None:
                current_engine = engine
                current_page_nums = [p.page_num]
            elif current_engine.engine_name == engine.engine_name:
                current_page_nums.append(p.page_num)
            else:
                groups.append((current_engine, current_page_nums))
                current_engine = engine
                current_page_nums = [p.page_num]

        if current_engine is not None and current_page_nums:
            groups.append((current_engine, current_page_nums))

        return groups

    def convert(
        self,
        pdf_path: Path,
        config: ConversionConfig,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> ConversionResult:
        """Execute full smart per-page routed conversion with Anti-OOM chunking."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"Input PDF does not exist: {pdf_path}")

        start_total = time.perf_counter()
        sha256_hash = compute_file_sha256(pdf_path)

        # 1. Pre-flight page inspection
        profiles = inspect_pdf(pdf_path, password=config.password)
        total_pages = len(profiles)

        # 2. Group contiguous pages by target engine
        engine_groups = self.group_pages_by_engine(profiles, config)

        results_by_page: dict[int, PageResult] = {}
        processed_count = 0

        # Open document safely inside context manager
        with fitz.open(str(pdf_path)) as doc:
            if doc.is_encrypted and config.password:
                if not doc.authenticate(config.password):
                    raise EncryptedPDFError(f"Invalid password for '{pdf_path.name}'.")

            for engine, page_nums in engine_groups:
                # Anti-OOM: Process pages in configurable batch chunks
                batch_size = max(1, config.batch_size)
                for i in range(0, len(page_nums), batch_size):
                    chunk = page_nums[i : i + batch_size]
                    for p_num in chunk:
                        page_res = engine.convert_page(doc, p_num, config)
                        results_by_page[p_num] = page_res
                        processed_count += 1

                        if on_progress:
                            on_progress(processed_count, total_pages, page_res.engine_used)

                    # Reclaim memory after each chunk
                    gc.collect()

        # 3. Assemble results strictly in original page order
        ordered_page_results = [results_by_page[p] for p in sorted(results_by_page.keys())]

        # 4. Post-processing pipeline
        final_markdown = postprocess_document(
            ordered_page_results,
            config=config,
            source_filename=pdf_path.name,
            sha256_hash=sha256_hash,
        )

        # 5. Write output file
        config.output_dir.mkdir(parents=True, exist_ok=True)
        output_file = config.output_dir / f"{pdf_path.stem}.md"
        output_file.write_text(final_markdown, encoding="utf-8")

        total_time_ms = (time.perf_counter() - start_total) * 1000
        engines_used = sorted(list({r.engine_used for r in ordered_page_results}))

        return ConversionResult(
            source_file=pdf_path,
            sha256=sha256_hash,
            total_pages=total_pages,
            pages=ordered_page_results,
            full_markdown=final_markdown,
            output_path=output_file,
            engines_used=engines_used,
            total_time_ms=round(total_time_ms, 2),
        )


def convert_pdf(
    pdf_path: Path,
    config: ConversionConfig,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> ConversionResult:
    """Convenience functional interface to convert a PDF using SmartRouter."""
    router = SmartRouter()
    return router.convert(pdf_path, config, on_progress=on_progress)
