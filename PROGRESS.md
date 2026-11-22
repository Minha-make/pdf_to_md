# OmniPDF2MD — Implementation Progress

| Phase | Description | Status | Verification Gate | Completed Date |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Workspace Scaffolding & Synthetic Test Suite | **PASSED** | **100% Passed** (Ruff, Mypy, Pytest) | 2026-11-21 |
| **Phase 1** | Core Architecture, Inspector, Fast Engine & CLI | **PASSED** | **100% Passed** (26/26 Tests, Gate 1) | 2026-11-21 |
| **Phase 2** | Deep Layout Engine (Docling), Local VLM & Smart Router | **PASSED** | **100% Passed** (37/37 Tests, Gate 2) | 2026-11-21 |
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
- [x] Built `src/omnipdf/core/inspector.py` performing per-page heuristic inspection.
- [x] Built Strategy Pattern base `src/omnipdf/core/engines/base.py` and Tier 1 `src/omnipdf/core/engines/fast_pymupdf.py` with asset image extraction.
- [x] Built `src/omnipdf/core/postprocess.py` (header/footer deduplication, LaTeX normalization, and YAML frontmatter).
- [x] Built `src/omnipdf/cli.py` with Typer & Rich.
- [x] Added unit tests: `test_models.py`, `test_inspector.py`, `test_fast_pymupdf.py`, `test_postprocess.py`, `test_cli.py`.
- [x] **Verification Gate 1 Passed:** 26/26 tests passed.
- [x] Pushed commit `ef30a5e` to `https://github.com/Minha-make/pdf_to_md`.

### Phase 2: Deep Layout Engine (Docling), Local VLM Fallback & Smart Router
- [x] Added `httpx` to dependencies and installed `docling` + `rapidocr` in `.venv`.
- [x] Built `src/omnipdf/core/engines/vlm_ollama.py` (Tier 3 VLM fallback via local Ollama `/api/chat` with multimodal image prompt and connection timeout/refusal guard).
- [x] Built `src/omnipdf/core/engines/deep_docling.py` (Tier 2 deep layout engine integrating Docling and RapidOCR with auto CPU/CUDA hardware detection).
- [x] Built `src/omnipdf/core/router.py` (SmartRouter with per-page dynamic routing, contiguous page grouping, batch chunking Anti-OOM, and progress callbacks).
- [x] Updated `src/omnipdf/cli.py` to route conversions through `SmartRouter` with real-time per-page status.
- [x] Added unit tests: `test_vlm_ollama.py`, `test_deep_docling.py`, `test_router.py`.
- [x] **Verification Gate 2 Passed:**
  - `omnipdf convert tests/fixtures/mixed.pdf --mode auto` confirmed multi-tier routing (Pages 1 & 4 via `pymupdf4llm`, Pages 2 & 3 via `docling`).
  - `scanned_sim.pdf` successfully transcribed via OCR with zero digital text layer.
  - Mock tests for `VLMOllamaEngine` confirmed response parsing and graceful fallback on connection failure.
  - `ruff check .` -> Clean (0 errors).
  - `mypy src tests` -> Clean (0 errors across 25 files).
  - `pytest -v` -> 37 passed in 42.15s.
