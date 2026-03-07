#!/usr/bin/env bash
# bootstrap-host.sh — Install all host-side build dependencies.
# Run once on the Ubuntu 24.04 build machine before calling `make iso`.
set -euo pipefail

REQUIRED_PACKAGES=(
    live-build
    debootstrap
    squashfs-tools
    xorriso
    syslinux-utils
    isolinux
    mtools
    dosfstools
    cryptsetup
    rsync
    curl
    wget
    jq
    git
    build-essential
    python3
    python3-pip
    python3-venv
)

echo "[bootstrap] Updating apt package lists..."
sudo apt-get update -qq

echo "[bootstrap] Installing required packages: ${REQUIRED_PACKAGES[*]}"
sudo apt-get install -y "${REQUIRED_PACKAGES[@]}"

echo ""
echo "[bootstrap] Verifying key tools..."
for cmd in lb debootstrap mksquashfs xorriso cryptsetup git python3; do
    if command -v "${cmd}" &>/dev/null; then
        echo "  [ok] ${cmd} -> $(command -v "${cmd}")"
    else
        echo "  [MISSING] ${cmd} — installation may have failed!"
    fi
done

echo ""
echo "[bootstrap] Host bootstrap complete. You can now run: make iso"
