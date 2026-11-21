"""Pre-flight page inspector and layout analyzer for OmniPDF2MD."""

import unicodedata
from pathlib import Path

import pymupdf as fitz

from omnipdf.core.models import EncryptedPDFError, PageProfile, PageType


def count_garbled_characters(text: str) -> int:
    """Count replacement, private-use area, and broken CMap characters."""
    garbled_count = 0
    for char in text:
        code = ord(char)
        # Unicode replacement character
        if char == "\ufffd":
            garbled_count += 1
        # Private Use Area (PUA) codepoints
        elif 0xE000 <= code <= 0xF8FF:
            garbled_count += 1
        # Control characters other than standard whitespace (\n, \r, \t)
        elif code < 32 and char not in ("\n", "\r", "\t"):
            garbled_count += 1
    return garbled_count


def calculate_image_coverage(page: fitz.Page) -> tuple[int, float]:
    """Calculate the count of images and the proportion of page area they cover."""
    page_rect = page.rect
    page_area = max(1.0, page_rect.width * page_rect.height)
    image_infos = page.get_image_info(xrefs=True)
    image_count = len(image_infos)

    if image_count == 0:
        # Check raw image list as fallback
        raw_images = page.get_images()
        if len(raw_images) > 0 and len(page.get_text().strip()) == 0:
            # Full-page raster scan without bbox info
            return len(raw_images), 1.0
        return 0, 0.0

    total_image_area = 0.0
    for info in image_infos:
        bbox = info.get("bbox")
        if bbox:
            x0, y0, x1, y1 = bbox
            area = max(0.0, (x1 - x0) * (y1 - y0))
            total_image_area += area

    ratio = min(1.0, total_image_area / page_area)
    return image_count, ratio


def detect_columns_and_tables(page: fitz.Page) -> tuple[int, bool]:
    """Detect whether a page contains multiple columns and/or tables."""
    page_width = page.rect.width
    blocks = page.get_text("blocks")
    # Filter text blocks (block_type == 0) with non-trivial text
    text_blocks = [b for b in blocks if b[6] == 0 and len(b[4].strip()) > 10]

    # Column detection: check for horizontal block separation overlapping vertically
    column_count = 1
    if len(text_blocks) >= 2:
        for i in range(len(text_blocks)):
            b1 = text_blocks[i]
            for j in range(i + 1, len(text_blocks)):
                b2 = text_blocks[j]
                # Check significant vertical overlap
                y_overlap = min(b1[3], b2[3]) - max(b1[1], b2[1])
                min_height = min(b1[3] - b1[1], b2[3] - b2[1])
                if min_height > 15 and y_overlap > 0.4 * min_height:
                    # Check clear horizontal separation on opposite sides of midpoint
                    b1_center_x = (b1[0] + b1[2]) / 2.0
                    b2_center_x = (b2[0] + b2[2]) / 2.0
                    if (b1_center_x < page_width * 0.48 and b2_center_x > page_width * 0.52) or (
                        b2_center_x < page_width * 0.48 and b1_center_x > page_width * 0.52
                    ):
                        column_count = 2
                        break
            if column_count >= 2:
                break

    # Table detection via PyMuPDF table finder or dense vector grid lines
    has_table = False
    try:
        tabs = page.find_tables()
        if len(tabs.tables) > 0:
            has_table = True
    except Exception:
        has_table = False

    if not has_table:
        drawings = page.get_drawings()
        if len(drawings) >= 10:
            # Check for intersecting horizontal and vertical line segments (tables)
            h_lines = 0
            v_lines = 0
            for d in drawings:
                rect = d.get("rect")
                if rect:
                    if (rect.x1 - rect.x0) > 40 and (rect.y1 - rect.y0) < 5:
                        h_lines += 1
                    elif (rect.y1 - rect.y0) > 40 and (rect.x1 - rect.x0) < 5:
                        v_lines += 1
            if h_lines >= 2 and v_lines >= 2:
                has_table = True

    return column_count, has_table


def inspect_page(page: fitz.Page, page_num: int) -> PageProfile:
    """Inspect and classify a single PDF page."""
    raw_text = page.get_text()
    clean_text = unicodedata.normalize("NFKC", raw_text)
    non_ws_chars = len([c for c in clean_text if not c.isspace()])

    image_count, image_area_ratio = calculate_image_coverage(page)
    column_count, has_table = detect_columns_and_tables(page)
    garbled_count = count_garbled_characters(raw_text)

    # Heuristic Classification
    # 1. Scanned Image
    if non_ws_chars < 50 and image_area_ratio > 0.55:
        page_type = PageType.SCANNED_IMAGE
        recommended_engine = "deep_docling_ocr"

    # 2. Garbled Encoding
    elif non_ws_chars >= 50 and (garbled_count > 5 or (garbled_count / non_ws_chars) > 0.02):
        page_type = PageType.GARBLED_ENCODING
        recommended_engine = "deep_docling_ocr"

    # 3. Complex Layout (Tables or Multi-column)
    elif has_table or column_count >= 2:
        page_type = PageType.COMPLEX_LAYOUT
        recommended_engine = "deep_docling"

    # 4. Digital Clean
    elif non_ws_chars >= 50 and image_area_ratio < 0.35:
        page_type = PageType.DIGITAL_CLEAN
        recommended_engine = "pymupdf4llm"

    # 5. Default Fallback
    elif non_ws_chars >= 50:
        page_type = PageType.DIGITAL_CLEAN
        recommended_engine = "pymupdf4llm"
    elif image_area_ratio > 0.40:
        page_type = PageType.SCANNED_IMAGE
        recommended_engine = "deep_docling_ocr"
    else:
        page_type = PageType.DIGITAL_CLEAN
        recommended_engine = "pymupdf4llm"

    return PageProfile(
        page_num=page_num,
        width=page.rect.width,
        height=page.rect.height,
        character_count=non_ws_chars,
        image_count=image_count,
        image_area_ratio=round(image_area_ratio, 4),
        column_count=column_count,
        has_table=has_table,
        garbled_char_count=garbled_count,
        page_type=page_type,
        recommended_engine=recommended_engine,
    )


def inspect_pdf(pdf_path: Path | str, password: str | None = None) -> list[PageProfile]:
    """Inspect all pages in a PDF and return a profile for each page."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file does not exist: {path}")

    with fitz.open(str(path)) as doc:
        if doc.is_encrypted:
            if not password or not doc.authenticate(password):
                raise EncryptedPDFError(
                    f"PDF is encrypted. Invalid or missing password for '{path.name}'."
                )

        profiles: list[PageProfile] = []
        for idx in range(len(doc)):
            page = doc[idx]
            profile = inspect_page(page, page_num=idx + 1)
            profiles.append(profile)

        return profiles
