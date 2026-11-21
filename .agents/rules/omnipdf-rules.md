---
trigger: always_on
description: Core engineering, Windows/Python safety, architecture, and testing rules for the OmniPDF2MD local app.
---

# OmniPDF2MD — Mandatory Agent Rules

## 1. Workflow & Scope Discipline
- **Single-Phase Execution:** Only implement the specific Phase requested by the user from `PLAN.md`. Never implement features belonging to future Phases.
- **Plan Before Code:** Before creating or modifying files in a new Phase, present a concise file-level Implementation Plan and wait for user approval.
- **Dependency Lock:** Do not install libraries outside `PLAN.md` without explicit user approval and a documented technical reason in `PROGRESS.md`.
- **Progress Tracking:** After passing a Phase's Verification Gate, update `PROGRESS.md` with completed items, test results, and known caveats.
- **3-Strike Error Escalation:** If a bug, dependency conflict, or test failure persists after 3 distinct fix attempts, STOP modifying code. Report the root-cause hypothesis, exact traceback, and proposed options to the user.

## 2. Environment & Platform Safety (Windows 11 + Python 3.12)
- **Virtual Environment:** Always execute `python`, `pip`, `pytest`, `ruff`, and `mypy` via the project's `.venv` (`.venv\Scripts\python.exe` on Windows). Never install packages globally.
- **Strict UTF-8 I/O:** Every `open()`, `Path.read_text()`, and `Path.write_text()` call MUST explicitly specify `encoding="utf-8"`. Never rely on OS default encoding (`cp1252`).
- **Deterministic Paths:** Use `pathlib.Path` exclusively for path manipulation. Never concatenate paths with raw `/` or `\` strings.
- **Prevent File Locking:** Always open PDFs, SQLite connections, and temporary files inside `with` context managers (e.g., `with fitz.open(path) as doc:`). Unclosed handles cause `PermissionError` on Windows during cleanup.
- **Subprocess & Shell:** Avoid bash-only syntax (e.g., `rm -rf`, `export VAR=...`) when running commands on Windows PowerShell. Prefer cross-platform Python scripts or PowerShell-safe commands.

## 3. Architecture & Code Quality
- **Strategy Pattern Integrity:** All PDF conversion backends under `src/omnipdf/core/engines/` MUST inherit from `BaseConverterEngine` and return standardized Pydantic v2 models defined in `core/models.py`.
- **Per-Page Routing:** Never classify an entire PDF as a single type if mixed pages exist. Route page-by-page via `core/inspector.py` and `core/router.py`.
- **Memory & Process Safety:** Process large PDFs in configurable page batches (default `batch_size=15`), release references, and invoke `gc.collect()` between batches. Heavy engine work must not block FastAPI's async event loop.
- **No Silent Failures:** `except Exception: pass` is strictly forbidden. Log errors with page numbers and context; if a single page fails unrecoverably, emit `<!-- [OmniPDF Warning: Page X failed: <reason>] -->` in the output Markdown.
- **Modern Typing:** Use Python 3.12 native type syntax (`list[str]`, `dict[str, Any]`, `Path | None`). All functions in `src/omnipdf/` must pass `mypy src/` and `ruff check .`.

## 4. PDF & Vietnamese Fidelity
- **Unicode Font in Fixtures:** When generating synthetic Vietnamese test PDFs (`tests/fixtures/`), MUST embed a true Unicode TTF font supporting Vietnamese diacritics (e.g., `C:\Windows\Fonts\arial.ttf` or `DejaVuSans.ttf`). Never use PyMuPDF's built-in `helv` font for Vietnamese text.
- **Garbled Text Guard:** Presence of a text layer does NOT guarantee clean digital text. Always check for replacement characters (`\ufffd`), Private Use Area codepoints, and broken Vietnamese diacritic sequences to trigger OCR/VLM fallback.
- **Relative Assets:** Save extracted images under `<output_dir>/assets/p{page:04d}_img{idx:02d}.png` and reference them via relative Markdown paths (`assets/...`).

## 5. Testing & Verification Anti-Cheating Rules
- **No Assertion Weakening:** Never delete, skip (`@pytest.mark.skip`), or weaken test assertions (e.g., changing content checks to `len(output) > 0`) merely to force a Verification Gate to pass.
- **Real Engine Verification:** Unit tests may mock external services (such as Ollama HTTP calls), but integration tests for `fast_pymupdf` and `deep_docling` MUST run against the real generated PDF fixtures.
- **Clean Workspace:** Never commit generated `.venv/`, `__pycache__/`, SQLite `.db` files, or large temporary output folders. Verify `git status` before concluding a Phase.