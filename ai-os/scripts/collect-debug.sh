#!/usr/bin/env bash
# collect-debug.sh — Collect debug information for AI-OS troubleshooting.
# Output: /tmp/ai-os-debug-<timestamp>.tar.gz
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TMPDIR_DEBUG=$(mktemp -d "/tmp/ai-os-debug-${TIMESTAMP}.XXXX")
OUTPUT="/tmp/ai-os-debug-${TIMESTAMP}.tar.gz"

echo "[collect-debug] Collecting AI-OS debug information..."
echo "[collect-debug] Temp directory: ${TMPDIR_DEBUG}"

# Helper to safely collect output
collect() {
    local label="$1"; shift
    local outfile="${TMPDIR_DEBUG}/${label}.txt"
    echo "  collecting: ${label}"
    "$@" > "${outfile}" 2>&1 || echo "(command failed)" >> "${outfile}"
}

# ── System info ───────────────────────────────────────────────────────────────
collect "uname"          uname -a
collect "os-release"     cat /etc/os-release
collect "uptime"         uptime
collect "lscpu"          lscpu
collect "meminfo"        cat /proc/meminfo
collect "df"             df -hT
collect "lsblk"          lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT
collect "mount"          mount

# ── AI-OS specific ────────────────────────────────────────────────────────────
collect "ai-modules"     ls -la /opt/modules/ 2>/dev/null || true
collect "mnt-modules"    ls -la /mnt/modules/ 2>/dev/null || true
collect "opt-ai"         ls -la /opt/ai/ 2>/dev/null || true
collect "vault-conf"     cat /etc/ai-os/vault.conf 2>/dev/null || echo "(no vault.conf)"
collect "install-conf"   cat /etc/ai-os/install.conf 2>/dev/null || echo "(no install.conf)"

# ── Security ──────────────────────────────────────────────────────────────────
collect "ufw-status"     ufw status verbose
collect "sysctl-ai"      cat /etc/sysctl.d/99-ai-os-hardening.conf 2>/dev/null || echo "(not present)"
collect "fail2ban-status" systemctl status fail2ban --no-pager

# ── Systemd / Logs ────────────────────────────────────────────────────────────
collect "systemd-failed" systemctl --failed --no-pager
collect "journalctl-boot" journalctl -b --no-pager -n 100

# ── Tool versions ─────────────────────────────────────────────────────────────
{
    echo "python3: $(python3 --version 2>&1)"
    echo "git:     $(git --version 2>&1)"
    echo "curl:    $(curl --version 2>&1 | head -1)"
    echo "ollama:  $(ollama --version 2>&1 || echo 'not installed')"
    echo "cryptsetup: $(cryptsetup --version 2>&1)"
    echo "mksquashfs: $(mksquashfs --version 2>&1 | head -1 || echo 'not installed')"
} > "${TMPDIR_DEBUG}/tool-versions.txt"

# ── GPU info ─────────────────────────────────────────────────────────────────
if command -v nvidia-smi &>/dev/null; then
    collect "nvidia-smi"  nvidia-smi
elif command -v rocm-smi &>/dev/null; then
    collect "rocm-smi"    rocm-smi
else
    echo "(no GPU tool)" > "${TMPDIR_DEBUG}/gpu.txt"
fi

# ── Package ───────────────────────────────────────────────────────────────────
collect "dpkg-list"      dpkg -l

# ── Create tarball ────────────────────────────────────────────────────────────
echo "[collect-debug] Creating archive: ${OUTPUT}"
tar -czf "${OUTPUT}" -C "$(dirname "${TMPDIR_DEBUG}")" "$(basename "${TMPDIR_DEBUG}")"

rm -rf "${TMPDIR_DEBUG}"

SIZE=$(du -sh "${OUTPUT}" | cut -f1)
echo ""
echo "[collect-debug] Debug bundle ready:"
echo "  ${OUTPUT}  (${SIZE})"
echo ""
echo "  Share this file when requesting support."
echo "  Note: vault.conf is included — review before sharing if sensitive."
