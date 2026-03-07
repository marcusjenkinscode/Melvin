#!/usr/bin/env bash
# build.sh — Build the AI-OS live ISO using live-build.
# Usage: bash build.sh
# Must be run from the ai-os/ directory on a properly bootstrapped Ubuntu host.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LB_DIR="${SCRIPT_DIR}/live-build"
ARTIFACT="${LB_DIR}/live-image-amd64.hybrid.iso"

echo "[build] Entering live-build directory: ${LB_DIR}"
cd "${LB_DIR}"

echo "[build] Cleaning previous build artifacts..."
sudo lb clean --all

echo "[build] Configuring live-build..."
sudo lb config

echo "[build] Building live ISO (this may take a while)..."
sudo lb build 2>&1 | tee "${SCRIPT_DIR}/build.log"

if [[ -f "${ARTIFACT}" ]]; then
    SIZE=$(du -sh "${ARTIFACT}" | cut -f1)
    echo ""
    echo "========================================="
    echo "[build] SUCCESS"
    echo "  Artifact : ${ARTIFACT}"
    echo "  Size     : ${SIZE}"
    echo "========================================="
else
    # live-build may name the output differently; find it
    ISO=$(find "${LB_DIR}" -maxdepth 1 -name "*.iso" | head -n 1 || true)
    if [[ -n "${ISO}" ]]; then
        SIZE=$(du -sh "${ISO}" | cut -f1)
        echo ""
        echo "========================================="
        echo "[build] SUCCESS"
        echo "  Artifact : ${ISO}"
        echo "  Size     : ${SIZE}"
        echo "========================================="
    else
        echo "[build] ERROR: ISO artifact not found after build."
        echo "  Check ${SCRIPT_DIR}/build.log for details."
        exit 1
    fi
fi
