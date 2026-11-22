#!/usr/bin/env bash
# OmniPDF2MD — One-Touch Unix/Linux/macOS Setup Script
# Requires: Python 3.12+, Node.js 18+ (optional for Web UI build)

set -e

echo "========================================"
echo "  OmniPDF2MD — Local Setup (POSIX)      "
echo "========================================"

# 1. Check Python 3.12
PYTHON_BIN=""
if command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN="python3.12"
elif command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    if [[ "$PY_VER" == 3.12* ]]; then
        PYTHON_BIN="python3"
    fi
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.12 is required but not found in PATH."
    exit 1
fi

echo "[1/4] Found Python: $($PYTHON_BIN --version)"

# 2. Virtual Environment Setup
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[2/4] Creating virtual environment at $VENV_DIR..."
    $PYTHON_BIN -m venv "$VENV_DIR"
else
    echo "[2/4] Virtual environment already exists at $VENV_DIR."
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
OMNIPDF_BIN="$VENV_DIR/bin/omnipdf"

# 3. Install Python Dependencies
echo "[3/4] Installing Python packages and OmniPDF CLI..."
$VENV_PYTHON -m pip install --upgrade pip --quiet
$VENV_PIP install -e ".[deep,api,dev]"

# 4. Build Web Studio Frontend (if npm is available)
if command -v npm >/dev/null 2>&1; then
    echo "[4/4] Building Web Studio UI (React + Tailwind)..."
    (
        cd web
        npm install --silent
        npm run build
    )
    echo "Web Studio build complete."
else
    echo "[4/4] [NOTICE] npm not found in PATH. Pre-built or development web UI will be skipped."
fi

# 5. Doctor Health Check
echo ""
echo "Running OmniPDF Doctor Diagnostic..."
$OMNIPDF_BIN doctor

echo ""
echo "=========================================================="
echo "  Setup Complete! OmniPDF2MD is ready to use.             "
echo "=========================================================="
echo ""
echo "Quick Start Commands:"
echo "  • Start Web Studio:    source .venv/bin/activate && omnipdf serve"
echo "  • Convert via CLI:     source .venv/bin/activate && omnipdf convert document.pdf -o output"
echo "  • Check System Health: source .venv/bin/activate && omnipdf doctor"
echo ""
