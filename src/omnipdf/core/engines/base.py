"""Abstract base class for all PDF converter engines."""

from abc import ABC, abstractmethod

import pymupdf as fitz

from omnipdf.core.models import ConversionConfig, PageResult


class BaseConverterEngine(ABC):
    """Abstract Strategy interface for PDF-to-Markdown converter engines."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Unique identifier name for this converter engine."""
        pass

    @abstractmethod
    def convert_page(
        self, doc: fitz.Document, page_num: int, config: ConversionConfig
    ) -> PageResult:
        """Convert a single page (1-based index) into standardized PageResult.

        Args:
            doc: An opened PyMuPDF Document instance.
            page_num: 1-based page number.
            config: Conversion configuration parameters.

        Returns:
            PageResult containing converted Markdown, extracted images, warnings, and duration.
        """
        pass

    def convert_batch(
        self, doc: fitz.Document, page_nums: list[int], config: ConversionConfig
    ) -> list[PageResult]:
        """Convert a batch of pages.

        Default implementation converts pages sequentially, but engines may override
        for batch optimizations.
        """
        results: list[PageResult] = []
        for p in page_nums:
            results.append(self.convert_page(doc, p, config))
        return results
