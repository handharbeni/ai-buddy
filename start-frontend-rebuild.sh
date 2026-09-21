#!/bin/bash
# Script to start the Next.js frontend for PM2 on Linux/macOS with rebuild
# This script assumes it's run from the project root (DBI-DB/);

PROJECT_ROOT="$(dirname "$0")"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

if [ ! -d "${FRONTEND_DIR}" ]; then
    echo "Error: Frontend directory not found at ${FRONTEND_DIR}."
    exit 1
fi

echo "Rebuilding frontend in ${FRONTEND_DIR}"
cd "${FRONTEND_DIR}"

# Ensure node_modules are present and updated
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install || { echo "npm install failed"; exit 1; }
else
    echo "Dependencies already installed. Running npm ci for consistency..."
    npm ci || { echo "npm ci failed"; exit 1; }
fi

echo "Building Next.js application..."
npm run build || { echo "npm run build failed"; exit 1; }

echo "Starting Next.js server..."
exec npm run start