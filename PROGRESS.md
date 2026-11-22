# OmniPDF2MD — Implementation Progress

| Phase | Description | Status | Verification Gate | Completed Date |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Workspace Scaffolding & Synthetic Test Suite | **PASSED** | **100% Passed** (Ruff, Mypy, Pytest) | 2026-11-21 |
| **Phase 1** | Core Architecture, Inspector, Fast Engine & CLI | **PASSED** | **100% Passed** (26/26 Tests, Gate 1) | 2026-11-21 |
| **Phase 2** | Deep Layout Engine (Docling), Local VLM & Smart Router | **PASSED** | **100% Passed** (37/37 Tests, Gate 2) | 2026-11-21 |
| **Phase 3** | Local Backend API, SQLite Storage & Real-time SSE | **PASSED** | **100% Passed** (41/41 Tests, Gate 3) | 2026-11-22 |
| **Phase 4** | Local Web Studio UI (React + Vite + Tailwind) | **PASSED** | **100% Passed** (Vite Build, Pytest 41/41, Ruff, Mypy) | 2026-11-22 |
| **Phase 5** | Unified Launcher, Packaging & Final Hardening | **PASSED** | **100% Passed** (43/43 Tests, Ruff, Mypy) | 2026-11-22 |

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

### Phase 4: Local Web Studio UI (React + Vite + Tailwind)
- [x] Scaffolding for React 18 + TypeScript + Vite + TailwindCSS in `web/`.
- [x] Configured Vite development proxy to `http://127.0.0.1:8765` and KaTeX rendering.
- [x] Implemented API client `src/api.ts` and data contracts `src/types.ts`.
- [x] Implemented SSE streaming hook `src/hooks/useJobProgress.ts` and hardware poller `src/hooks/useSystemStatus.ts`.
- [x] Created `src/components/Header.tsx` displaying system compute device (CPU/CUDA), Ollama VLM status, and queue depth.
- [x] Created `src/components/UploadDropzone.tsx` supporting drag-and-drop, conversion mode selection (`auto`, `fast`, `deep`), encrypted PDF password input, and image extraction options.
- [x] Created `src/components/JobList.tsx` displaying live conversion progress bars, engine tags, and cancel action.
- [x] Created `src/components/PDFViewer.tsx` using `pdfjs-dist` for multi-page canvas rendering, navigation, and zoom.
- [x] Created `src/components/MarkdownViewer.tsx` using `react-markdown`, `remark-gfm`, `remark-math`, `rehype-katex`, with asset image rewriting to `/api/jobs/{id}/assets/...`.
- [x] Created `src/components/MarkdownEditor.tsx` with live word/line counters.
- [x] Created `src/components/ExportToolbar.tsx` for clipboard copy, `.md` download, and `.zip` download.
- [x] Created `src/components/SplitPaneViewer.tsx` uniting side-by-side inspection.
- [x] Added `GET /api/jobs/{job_id}/file` in backend to serve original PDF files to the web canvas renderer.
- [x] **Verification Gate 4 Passed:**
  - `npm run build` in `web/` succeeded with 0 TypeScript/Vite errors.
  - `tests/integration/test_api_lifecycle.py` verified original PDF file streaming.
  - Full pytest suite: 41/41 tests passed in 51.18s.
  - `ruff check .` -> Clean (0 errors).
  - `mypy src tests` -> Clean (0 errors across 34 files).
  - Clean git workspace with `web/node_modules/` and `web/dist/` ignored.

### Phase 5: Unified Launcher, Packaging & Final Hardening
- [x] Configured FastAPI in `src/omnipdf/api/main.py` with dynamic `web/dist` mounting, SPA fallback routing, and non-dist diagnostic landing.
- [x] Implemented `omnipdf serve` CLI command in `src/omnipdf/cli.py` with options (`--host`, `--port`, `--open/--no-open`, `--reload`), Rich startup panel, and background browser auto-open.
- [x] Created one-touch setup scripts:
  - `setup.ps1` (Windows 11 PowerShell automated bootstrap).
  - `setup.sh` (POSIX cross-platform automated bootstrap).
- [x] Comprehensive documentation overhaul in `README.md` (features, Mermaid architecture, multi-tier comparison table, quickstart, CLI reference, Web Studio overview, NVIDIA CUDA instructions, Ollama setup, and Vietnamese typography fidelity).
- [x] Created `tests/integration/test_serve_app.py` verifying static file serving, SPA client-side routing, static assets delivery, and fallback landing.
- [x] Reinstalled package in editable mode (`pip install -e .`) linking `omnipdf` executable.
- [x] **Verification Gate 5 Passed (Final Acceptance):**
  - Full pytest suite: 43/43 tests passed in 46.18s.
  - `ruff check .` -> Clean (0 errors).
  - `mypy src tests` -> Clean (0 errors across 35 source files).
  - Clean git workspace verified.


