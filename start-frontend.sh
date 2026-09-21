#!/bin/bash
# Script to start the Next.js frontend for PM2 on Linux/macOS
# This script assumes it's run from the project root (DBI-DB/)

PROJECT_ROOT="$(dirname "$0")"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

if [ ! -d "${FRONTEND_DIR}" ]; then
    echo "Error: Frontend directory not found at ${FRONTEND_DIR}. Please run 'npm install && npm run build' in frontend directory."
    exit 1
fi

echo "Starting frontend in ${FRONTEND_DIR}"
cd "${FRONTEND_DIR}"
exec npm run start