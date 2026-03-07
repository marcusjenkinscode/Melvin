#!/usr/bin/env bash
# install-post.sh — Post-installation tasks for AI-OS.
# Run once after first boot on the installed system (as root).
set -euo pipefail

echo "[install-post] === AI-OS Post-Installation Setup ==="

# ── Ensure required directories exist ────────────────────────────────────────
echo "[install-post] Creating required directories..."
install -d -m 0750 /opt/ai/models
install -d -m 0755 /opt/ai/workspaces
install -d -m 0755 /opt/modules
install -d -m 0755 /mnt/modules
install -d -m 0700 /etc/ai-os

# ── Set correct PATH for AI tools ─────────────────────────────────────────────
echo "[install-post] Ensuring /usr/local/bin is in system PATH..."
if ! grep -q "usr/local/bin" /etc/environment 2>/dev/null; then
    echo 'PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"' \
        >> /etc/environment
fi

# ── Update package lists ──────────────────────────────────────────────────────
echo "[install-post] Updating apt package cache..."
apt-get update -qq

# ── Install any missing essentials ───────────────────────────────────────────
MISSING_PKGS=(cryptsetup squashfs-tools curl wget jq git)
TO_INSTALL=()
for pkg in "${MISSING_PKGS[@]}"; do
    if ! dpkg -l "${pkg}" 2>/dev/null | grep -q "^ii"; then
        TO_INSTALL+=("${pkg}")
    fi
done

if [[ ${#TO_INSTALL[@]} -gt 0 ]]; then
    echo "[install-post] Installing missing packages: ${TO_INSTALL[*]}"
    apt-get install -y "${TO_INSTALL[@]}"
fi

# ── Mark install complete ─────────────────────────────────────────────────────
echo "installed=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /etc/ai-os/install.conf

echo ""
echo "[install-post] === Post-installation complete ==="
echo "  Next steps:"
echo "  1. Set up the encrypted model vault:  setup-model-vault --device <device>"
echo "  2. Choose an AI hardware profile:     ai-profile {cpu|nvidia|amd}"
echo "  3. Harden the system:                 harden-system"
echo "  4. Verify the installation:           bash /path/to/scripts/verify-system.sh"
