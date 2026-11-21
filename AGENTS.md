# OmniPDF2MD — Agent Engineering & Architectural Rules

## 1. Scope & Execution Discipline
- **Single-Phase Execution:** Only execute the phase currently in scope from `plan.md`. Never preemptively write features for future phases.
- **Plan Before Code:** Before creating or modifying files in any new phase, present a concise implementation plan artifact and await user approval.
- **Dependency Lock:** Only install dependencies listed in `plan.md`. Document any changes in `PROGRESS.md`.
- **Progress Tracking:** Update `PROGRESS.md` with completed milestones, test outputs, and known caveats after passing every Verification Gate.
- **3-Strike Escalation:** Stop modifying code after 3 unsuccessful attempts at fixing a bug or test failure. Escalate with traceback and proposed options.

## 2. Windows 11 & Python 3.12 Platform Guardrails
- **Virtual Environment:** Always run Python, Pip, Pytest, Ruff, and Mypy through `.venv\Scripts\python.exe` (Windows). Never install packages globally.
- **Strict UTF-8 I/O:** Every `open()`, `Path.read_text()`, and `Path.write_text()` MUST explicitly specify `encoding="utf-8"`.
- **Deterministic Paths:** Exclusively use `pathlib.Path`. Do not concatenate strings with `/` or `\`.
- **Resource Cleanup (Prevent Windows File Locking):** Always use `with` context managers for PDFs (`with fitz.open(path) as doc:`), SQLite connections, and temporary files.
- **Cross-Platform Shell:** Avoid Bash-only syntax (`rm -rf`, `export`). Prefer PowerShell-safe commands or Python scripts.

## 3. Architecture & Code Quality
- **Strategy Pattern:** All engines inherit from `BaseConverterEngine` and return standardized Pydantic v2 models.
- **Per-Page Routing:** Classify pages individually via `inspector.py` and `router.py`.
- **Memory Safety:** Process large PDFs in batches (default 15 pages), releasing references and calling `gc.collect()`.
- **No Silent Failures:** Never write `except Exception: pass`. Log context with page numbers; emit `<!-- [OmniPDF Warning: Page X failed: <reason>] -->` if unrecoverable.
- **Strict Typing & Linting:** Python 3.12 syntax (`list[str]`, `dict[str, Any]`, `Path | None`). Must pass `ruff check .` and `mypy src/ tests/`.

## 4. Typography & Testing Integrity
- **Vietnamese Unicode Fixtures:** Test PDF generators must embed true TTF Unicode fonts (`C:\Windows\Fonts\arial.ttf`). Never use PyMuPDF built-in `helv` font for Vietnamese diacritics.
- **Garbled Text Guard:** Check for replacement characters (`\ufffd`), PUA codepoints, and broken diacritic marks.
- **No Assertion Weakening:** Never skip or weaken test assertions to force a gate to pass.
- **Clean Workspace:** Never commit `.venv/`, `__pycache__/`, SQLite `.db` files, or generated PDF fixtures.
