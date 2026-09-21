#!/bin/bash
# Script to start the FastAPI backend for PM2 on Linux/macOS
# This script assumes it's run from the project root (DBI-DB/)

PROJECT_ROOT="$(dirname "$0")"
BACKEND_DIR="${PROJECT_ROOT}/backend"
VENV_PYTHON="${BACKEND_DIR}/venv/bin/python" # Linux/macOS venv path

if [ ! -f "${VENV_PYTHON}" ]; then
    echo "Error: Python venv not found at ${VENV_PYTHON}. Please run 'source backend/venv/bin/activate && pip install .' in backend directory."
    exit 1
fi

echo "Starting backend with ${VENV_PYTHON}"
exec "${VENV_PYTHON}" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2