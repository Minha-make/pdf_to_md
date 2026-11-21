# OmniPDF2MD — Implementation Progress

| Phase | Description | Status | Verification Gate | Completed Date |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Workspace Scaffolding & Synthetic Test Suite | **PASSED** | **100% Passed** (Ruff, Mypy, Pytest) | 2026-11-21 |
| **Phase 1** | Core Architecture, Inspector, Fast Engine & CLI | **PASSED** | **100% Passed** (26/26 Tests, Gate 1) | 2026-11-21 |
| **Phase 2** | Deep Layout Engine (Docling), Local VLM & Smart Router | Not Started | Pending | - |
| **Phase 3** | Local Backend API, SQLite Storage & Real-time SSE | Not Started | Pending | - |
| **Phase 4** | Local Web Studio UI (React + Vite + Tailwind) | Not Started | Pending | - |
| **Phase 5** | Unified Launcher, Packaging & Final Hardening | Not Started | Pending | - |

---

## Phase Details & Audit Log

### Phase 0: Workspace Scaffolding & Synthetic Test Suite
- [x] Initialized Git repository on `main` branch with remote `https://github.com/Minha-make/pdf_to_md`.
- [x] Configured `.gitignore` for Python, venv, caches, and PDF test binaries.
- [x] Created `pyproject.toml` with Python 3.12, strict Ruff, Mypy, and Pytest configs.
- [x] Created `AGENTS.md` and `README.md` documenting strict engineering rules and project overview.
- [x] Installed base dependencies in `.venv` (`pymupdf`, `pymupdf4llm`, `pillow`, `pydantic`, `typer`, `rich`, `pytest`, `ruff`, `mypy`).
- [x] Created `tests/fixtures/generate_samples.py` generating 5 standardized synthetic PDF fixtures using TrueType Unicode font (`C:\Windows\Fonts\arial.ttf`).
- [x] Created `tests/unit/test_fixtures_generation.py`.
- [x] **Verification Gate 0 Passed:**
  - `python tests/fixtures/generate_samples.py` -> 5/5 valid PDF fixtures created.
  - `ruff check .` -> Clean (0 errors).
  - `mypy src tests` -> Clean (0 errors across 6 files).
  - `pytest -v` -> 5 passed in 0.53s.
- [x] Pushed commit `8795594` to `https://github.com/Minha-make/pdf_to_md`.

### Phase 1: Core Architecture, Inspector, Fast Engine & CLI
- [x] Created `src/omnipdf/config.py` with Pydantic settings.
- [x] Built `src/omnipdf/core/models.py` with standard Pydantic v2 schemas (`PageProfile`, `PageType`, `ConversionConfig`, `PageResult`, `ConversionResult`) and domain exceptions.
- [x] Built `src/omnipdf/core/inspector.py` performing per-page heuristic inspection (text density, image coverage ratio, multi-column analysis, table detection, garbled encoding checks, and AES password validation).
- [x] Built Strategy Pattern base `src/omnipdf/core/engines/base.py` and Tier 1 `src/omnipdf/core/engines/fast_pymupdf.py` with asset image extraction (`assets/p{page:04d}_img{idx:02d}.png`).
- [x] Built `src/omnipdf/core/postprocess.py` (header/footer deduplication > 60% pages, LaTeX `$`/`$$` normalization, blank line formatting, and YAML frontmatter).
- [x] Built `src/omnipdf/cli.py` with Typer & Rich: `omnipdf convert` and `omnipdf doctor`.
- [x] Added unit tests: `test_models.py`, `test_inspector.py`, `test_fast_pymupdf.py`, `test_postprocess.py`, `test_cli.py`.
- [x] **Verification Gate 1 Passed:**
  - `inspector.py` classified 100% of pages correctly across all 5 fixture documents.
  - `clean_vn.pdf` converted to Markdown with perfect Vietnamese UTF-8 diacritics.
  - `encrypted.pdf` rejected without password; decrypted and converted with `secret123`.
  - `mixed.pdf` extracted embedded images into `assets/p0004_img01.png`.
  - `ruff check .` -> Clean (0 errors).
  - `mypy src tests` -> Clean (0 errors across 19 files).
  - `pytest -v` -> 26 passed in 6.34s.
