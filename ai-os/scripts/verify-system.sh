#!/usr/bin/env bash
# verify-system.sh — Verify AI-OS system installation state.
# Can be run without root for most checks; some checks require root.
set -euo pipefail

PASS=0
WARN=0
FAIL=0

ok()   { echo "  [PASS] $*"; (( PASS++ )); }
warn() { echo "  [WARN] $*"; (( WARN++ )); }
fail() { echo "  [FAIL] $*"; (( FAIL++ )); }

echo "========================================="
echo " AI-OS System Verification"
echo " $(date)"
echo "========================================="

# ── Required directories ──────────────────────────────────────────────────────
echo ""
echo "--- Directory Layout ---"
for dir in /opt/ai/models /opt/ai/workspaces /opt/modules /mnt/modules; do
    if [[ -d "${dir}" ]]; then
        ok "${dir} exists"
    else
        fail "${dir} MISSING"
    fi
done

# ── Required binaries ─────────────────────────────────────────────────────────
echo ""
echo "--- Required Binaries ---"
for cmd in activate-module deactivate-module unlock-models lock-models \
           setup-model-vault harden-system ai-benchmark ai-profile; do
    if command -v "${cmd}" &>/dev/null; then
        ok "${cmd} found at $(command -v "${cmd}")"
    else
        fail "${cmd} NOT FOUND in PATH"
    fi
done

# ── System tools ──────────────────────────────────────────────────────────────
echo ""
echo "--- System Tools ---"
for cmd in cryptsetup mksquashfs mount umount ufw python3 git curl; do
    if command -v "${cmd}" &>/dev/null; then
        ok "${cmd} available"
    else
        warn "${cmd} not found"
    fi
done

# ── Ollama ────────────────────────────────────────────────────────────────────
echo ""
echo "--- Ollama ---"
if command -v ollama &>/dev/null; then
    ok "ollama installed: $(ollama --version 2>/dev/null || echo 'version unknown')"
else
    warn "ollama not installed (run: ai-profile cpu)"
fi

# ── Security ──────────────────────────────────────────────────────────────────
echo ""
echo "--- Security ---"
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | head -1 || echo "unknown")
    if echo "${UFW_STATUS}" | grep -q "active"; then
        ok "UFW is active"
    else
        warn "UFW is not active (run: harden-system)"
    fi
else
    warn "ufw not installed"
fi

if systemctl is-active --quiet fail2ban 2>/dev/null; then
    ok "fail2ban is running"
else
    warn "fail2ban is not running (run: harden-system)"
fi

if [[ -f /etc/sysctl.d/99-ai-os-hardening.conf ]]; then
    ok "sysctl hardening file present"
else
    warn "sysctl hardening not applied (run: harden-system)"
fi

# ── Vault config ──────────────────────────────────────────────────────────────
echo ""
echo "--- Model Vault ---"
if [[ -f /etc/ai-os/vault.conf ]]; then
    ok "vault.conf present"
    # shellcheck source=/dev/null
    source /etc/ai-os/vault.conf 2>/dev/null || true
    if mountpoint -q /opt/ai/models 2>/dev/null; then
        ok "/opt/ai/models is mounted"
    else
        warn "/opt/ai/models not mounted (run: unlock-models)"
    fi
else
    warn "vault not configured (run: setup-model-vault)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo " Results: ${PASS} passed | ${WARN} warnings | ${FAIL} failures"
echo "========================================="

if (( FAIL > 0 )); then
    echo " OVERALL: FAIL — address failures above before use."
    exit 1
elif (( WARN > 0 )); then
    echo " OVERALL: WARN — system usable but review warnings above."
    exit 0
else
    echo " OVERALL: PASS — system looks good."
    exit 0
fi
