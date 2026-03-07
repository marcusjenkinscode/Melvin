#!/usr/bin/env bash
# build-module-dev-tools.sh — Build the dev-tools squashfs overlay module.
# Output: /opt/modules/dev-tools.squashfs  (or ./dev-tools.squashfs locally)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_NAME="dev-tools"
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
    install -d -m 0755 "${ROOT_DIR}/opt/dev-tools/bin"
    install -d -m 0755 "${ROOT_DIR}/opt/dev-tools/share"
    # Placeholder README
    cat > "${ROOT_DIR}/opt/dev-tools/README.md" <<'EOF'
# dev-tools module
This squashfs overlay provides development tooling for AI-OS.
Populate this module by copying binaries, configs or scripts into root-dev-tools/.
EOF
    # Placeholder activation helper
    cat > "${ROOT_DIR}/opt/dev-tools/bin/dev-tools-info" <<'SCRIPT'
#!/usr/bin/env bash
echo "dev-tools module is active."
echo "Contents: $(ls /opt/dev-tools/)"
SCRIPT
    chmod +x "${ROOT_DIR}/opt/dev-tools/bin/dev-tools-info"
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
