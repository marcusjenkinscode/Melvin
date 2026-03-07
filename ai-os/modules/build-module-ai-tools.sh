#!/usr/bin/env bash
# build-module-ai-tools.sh — Build the ai-tools squashfs overlay module.
# Output: /opt/modules/ai-tools.squashfs  (or ./ai-tools.squashfs locally)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_NAME="ai-tools"
ROOT_DIR="${SCRIPT_DIR}/root-${MODULE_NAME}"
OUTPUT_DIR="${SCRIPT_DIR}/../live-build/binary/opt/modules"
OUTPUT_FILE="${OUTPUT_DIR}/${MODULE_NAME}.squashfs"

# Allow local testing: if not in live-build context, write alongside script
if [[ ! -d "$(dirname "${OUTPUT_DIR}")" ]]; then
    OUTPUT_DIR="${SCRIPT_DIR}"
    OUTPUT_FILE="${OUTPUT_DIR}/${MODULE_NAME}.squashfs"
fi

echo "[build-module] Building module: ${MODULE_NAME}"
echo "[build-module] Module root    : ${ROOT_DIR}"
echo "[build-module] Output         : ${OUTPUT_FILE}"

# Create basic placeholder structure in module root if empty
if [[ -z "$(ls -A "${ROOT_DIR}" 2>/dev/null)" ]] || \
   [[ "$(ls "${ROOT_DIR}")" == ".gitkeep" ]]; then
    echo "[build-module] Populating placeholder module root..."
    install -d -m 0755 "${ROOT_DIR}/opt/ai-tools/bin"
    install -d -m 0755 "${ROOT_DIR}/opt/ai-tools/models"
    install -d -m 0755 "${ROOT_DIR}/opt/ai-tools/venv"
    # Placeholder README
    cat > "${ROOT_DIR}/opt/ai-tools/README.md" <<'EOF'
# ai-tools module
This squashfs overlay provides AI tooling for AI-OS.
Populate this module by running pip installs or copying binaries into root-ai-tools/.
EOF
    # Placeholder activation helper
    cat > "${ROOT_DIR}/opt/ai-tools/bin/ai-tools-info" <<'SCRIPT'
#!/usr/bin/env bash
echo "ai-tools module is active."
echo "Contents: $(ls /opt/ai-tools/)"
SCRIPT
    chmod +x "${ROOT_DIR}/opt/ai-tools/bin/ai-tools-info"
fi

mkdir -p "${OUTPUT_DIR}"

echo "[build-module] Running mksquashfs..."
mksquashfs "${ROOT_DIR}" "${OUTPUT_FILE}" \
    -comp zstd \
    -Xcompression-level 19 \
    -b 1M \
    -noappend \
    -no-progress

SIZE=$(du -sh "${OUTPUT_FILE}" | cut -f1)
echo "[build-module] Done: ${OUTPUT_FILE} (${SIZE})"
