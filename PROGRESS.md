# OmniPDF2MD — Implementation Progress

| Phase | Description | Status | Verification Gate | Completed Date |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Workspace Scaffolding & Synthetic Test Suite | **PASSED** | **100% Passed** (Ruff, Mypy, Pytest) | 2026-11-21 |
| **Phase 1** | Core Architecture, Inspector, Fast Engine & CLI | **PASSED** | **100% Passed** (26/26 Tests, Gate 1) | 2026-11-21 |
| **Phase 2** | Deep Layout Engine (Docling), Local VLM & Smart Router | **PASSED** | **100% Passed** (37/37 Tests, Gate 2) | 2026-11-21 |
| **Phase 3** | Local Backend API, SQLite Storage & Real-time SSE | **PASSED** | **100% Passed** (41/41 Tests, Gate 3) | 2026-11-22 |
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
- [x] **Verification Gate 0 Passed:** 5/5 valid PDF fixtures created, Ruff/Mypy clean, Pytest passed.
- [x] Pushed commit `8795594` to GitHub.

### Phase 1: Core Architecture, Inspector, Fast Engine & CLI
- [x] Created `src/omnipdf/config.py` and `src/omnipdf/core/models.py`.
- [x] Built `src/omnipdf/core/inspector.py` performing per-page heuristic inspection.
- [x] Built Strategy Pattern base `core/engines/base.py` and Tier 1 `core/engines/fast_pymupdf.py`.
- [x] Built `core/postprocess.py` and `cli.py`.
- [x] **Verification Gate 1 Passed:** 26/26 tests passed.
- [x] Pushed commit `ef30a5e` to GitHub.

### Phase 2: Deep Layout Engine (Docling), Local VLM Fallback & Smart Router
- [x] Built `core/engines/vlm_ollama.py` and `core/engines/deep_docling.py`.
- [x] Built `core/router.py` (SmartRouter with Anti-OOM chunking and contiguous page grouping).
- [x] Updated `cli.py` to route conversions through `SmartRouter`.
- [x] **Verification Gate 2 Passed:** 37/37 tests passed.
- [x] Pushed commit `556a9f9` to GitHub.

### Phase 3: Local Backend API, SQLite Storage & Real-time Streaming
- [x] Built `storage/db.py` (async SQLite via `aiosqlite` with WAL mode and SHA-256 Hash Caching).
- [x] Built `storage/workspace.py` (upload byte validation against corrupted files and ZIP bundling).
- [x] Built `api/worker.py` (sequential queue consumer preventing concurrent OCR memory spikes, SSE pub/sub broadcaster, and job cancellation).
- [x] Built `api/routes.py` and `api/main.py` (FastAPI app with endpoints `POST /api/jobs`, `GET /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, `POST /api/jobs/{id}/cancel`, `GET /api/jobs/{id}/result`, `GET /api/jobs/{id}/download`, `GET /api/system/status`).
- [x] Created `tests/integration/test_api_lifecycle.py` verifying full lifecycle.
- [x] **Verification Gate 3 Passed:**
  - Corrupted PDF upload correctly rejected with HTTP 400 Bad Request.
  - End-to-end job completion with Markdown result and ZIP bundle download.
  - Re-upload with same SHA-256 verified instantaneous Hash Cache hit (`cached: true`).
  - Job cancellation endpoint verified.
  - System status endpoint verified (`GET /api/system/status`).
  - `ruff check .` -> Clean (0 errors).
  - `mypy src tests` -> Clean (0 errors across 34 files).
  - `pytest -v` -> 41 passed in 30.40s.
