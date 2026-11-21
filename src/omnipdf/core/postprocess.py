"""Post-processing pipeline for cleaning, unifying, and standardizing Markdown output."""

import re
from datetime import UTC, datetime
from typing import Any

import yaml

from omnipdf.core.models import ConversionConfig, PageResult


def normalize_latex(text: str) -> str:
    """Standardize LaTeX mathematical expressions to $...$ and $$...$$ syntax."""
    # Convert block math \[ ... \] to $$ ... $$
    block_pattern = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
    text = block_pattern.sub(r"$$\n\1\n$$", text)

    # Convert inline math \( ... \) to $ ... $
    inline_pattern = re.compile(r"\\\((.*?)\\\)")
    text = inline_pattern.sub(r"$\1$", text)

    return text


def normalize_whitespace(text: str) -> str:
    """Normalize line endings and collapse excessive consecutive blank lines."""
    # Normalize line endings to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Collapse 3 or more consecutive newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def deduplicate_headers_footers(page_markdowns: list[str]) -> list[str]:
    """Remove repetitive headers and footers appearing across > 60% of pages."""
    if len(page_markdowns) < 3:
        return page_markdowns

    threshold = 0.60 * len(page_markdowns)

    def extract_bounds(md: str) -> tuple[str | None, str | None]:
        lines = [line.strip() for line in md.split("\n") if line.strip()]
        top = lines[0] if lines else None
        bottom = lines[-1] if len(lines) > 1 else None
        return top, bottom

    def normalize_pattern(line: str) -> str:
        # Replace digits with # to account for varying page numbers
        return re.sub(r"\d+", "#", line)

    top_patterns: dict[str, int] = {}
    bottom_patterns: dict[str, int] = {}

    for md in page_markdowns:
        top, bottom = extract_bounds(md)
        if top:
            pat = normalize_pattern(top)
            top_patterns[pat] = top_patterns.get(pat, 0) + 1
        if bottom:
            pat = normalize_pattern(bottom)
            bottom_patterns[pat] = bottom_patterns.get(pat, 0) + 1

    common_top = {pat for pat, count in top_patterns.items() if count >= threshold}
    common_bottom = {pat for pat, count in bottom_patterns.items() if count >= threshold}

    if not common_top and not common_bottom:
        return page_markdowns

    cleaned_pages: list[str] = []
    for md in page_markdowns:
        lines = md.split("\n")
        # Remove matching top line
        while lines and (not lines[0].strip() or normalize_pattern(lines[0].strip()) in common_top):
            lines.pop(0)
        # Remove matching bottom line
        while lines and (
            not lines[-1].strip() or normalize_pattern(lines[-1].strip()) in common_bottom
        ):
            lines.pop()
        cleaned_pages.append("\n".join(lines))

    return cleaned_pages


def generate_frontmatter(metadata: dict[str, Any]) -> str:
    """Generate YAML frontmatter header string."""
    yaml_str = yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n"


def postprocess_document(
    pages: list[PageResult],
    config: ConversionConfig,
    source_filename: str = "document.pdf",
    sha256_hash: str = "",
) -> str:
    """Post-process all page results and assemble into a unified Markdown document."""
    page_texts = [p.markdown for p in pages]

    # 1. Deduplicate recurring headers and footers across pages
    page_texts = deduplicate_headers_footers(page_texts)

    # 2. Join pages separated by page-break comments
    joined_body = "\n\n<!-- --- Page Break --- -->\n\n".join(page_texts)

    # 3. Standardize LaTeX math syntax
    cleaned_body = normalize_latex(joined_body)

    # 4. Standardize blank lines and whitespace
    cleaned_body = normalize_whitespace(cleaned_body)

    # 5. Prepend YAML frontmatter if requested
    if config.include_frontmatter:
        engines_used = sorted(list({p.engine_used for p in pages}))
        metadata = {
            "source_file": source_filename,
            "sha256": sha256_hash,
            "total_pages": len(pages),
            "engines_used": engines_used,
            "converted_at": datetime.now(UTC).isoformat(),
        }
        frontmatter = generate_frontmatter(metadata)
        return frontmatter + cleaned_body

    return cleaned_body
