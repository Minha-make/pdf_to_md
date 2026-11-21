# OmniPDF2MD

Universal, 100% local, offline-capable PDF-to-Markdown converter with smart per-page routing and OCR fallback.

## Features
- **Smart Per-Page Routing**: Analyzes each page individually (Digital Clean, Complex Layout, Scanned Raster, Garbled CMap).
- **Multi-Tier Conversion**: Fast conversion via PyMuPDF4LLM, deep layout/OCR via Docling, and local VLM fallback via Ollama.
- **Strict Vietnamese Typography**: Full support for Unicode Vietnamese diacritics without broken glyphs.
- **Anti-OOM & Memory Protection**: Page batching and deterministic process/file handling.
- **Local Web Studio & CLI**: Typer CLI + FastAPI + React frontend.
