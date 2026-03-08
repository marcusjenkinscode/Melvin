#!/data/data/com.termux/files/usr/bin/bash
# ============================================================
# ssh_setup.sh – set up SSH keys in Termux for VPS access
# ============================================================
# Run this after a fresh VPS reinstall, or whenever SSH access
# from Termux stops working due to changed host keys or missing
# client keys.
#
# Usage (inside Termux):
#   chmod +x ssh_setup.sh
#   ./ssh_setup.sh
#
# What it does:
#   1. Installs openssh (if not already installed)
#   2. Creates ~/.ssh with correct permissions
#   3. Generates a new Ed25519 key pair (if none exists)
#   4. Optionally removes a stale known_hosts entry for your VPS
#   5. Prints your public key and copy-it-to-VPS instructions
# ============================================================

set -e

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
_info()    { echo "  $*"; }
_ok()      { echo "  ✓  $*"; }
_warn()    { echo "  [!] $*"; }
_heading() { echo ""; echo "▶  $*"; }

SSH_DIR="$HOME/.ssh"
KEY_FILE="$SSH_DIR/id_ed25519"
PUB_FILE="${KEY_FILE}.pub"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Melvin – SSH Key Setup (Termux)        ║"
echo "╚══════════════════════════════════════════╝"

# ------------------------------------------------------------
# 1. Install openssh
# ------------------------------------------------------------
_heading "Checking for openssh…"
if command -v ssh-keygen >/dev/null 2>&1; then
    _ok "openssh is already installed."
else
    _info "Installing openssh via pkg…"
    pkg install -y openssh
    _ok "openssh installed."
fi

# ------------------------------------------------------------
# 2. Create ~/.ssh with correct permissions
# ------------------------------------------------------------
_heading "Setting up ~/.ssh directory…"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"
_ok "~/.ssh exists with mode 700."

# ------------------------------------------------------------
# 3. Generate Ed25519 key pair (skip if one already exists)
# ------------------------------------------------------------
_heading "Checking for existing SSH key pair…"
if [ -f "$KEY_FILE" ]; then
    _ok "Key pair already exists at $KEY_FILE"
    _info "Skipping key generation (delete $KEY_FILE to force regeneration)."
else
    _info "Generating new Ed25519 key pair…"
    ssh-keygen -t ed25519 -C "termux-melvin" -f "$KEY_FILE" -N ""
    chmod 600 "$KEY_FILE"
    chmod 644 "$PUB_FILE"
    _ok "Key pair created: $KEY_FILE"
fi

# ------------------------------------------------------------
# 4. Remove stale known_hosts entry (optional)
# ------------------------------------------------------------
_heading "Stale VPS host-key cleanup…"
echo ""
echo "  After reinstalling a VPS the server's host key changes."
echo "  SSH will refuse to connect with:"
echo "    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!"
echo ""
printf "  Enter your VPS hostname or IP (leave blank to skip): "
read -r VPS_HOST

if [ -n "$VPS_HOST" ]; then
    KNOWN_HOSTS="$SSH_DIR/known_hosts"
    if [ -f "$KNOWN_HOSTS" ]; then
        # Remove any existing entries for this host (plain and hashed)
        ssh-keygen -R "$VPS_HOST" 2>/dev/null && \
            _ok "Removed stale entry for '$VPS_HOST' from known_hosts." || \
            _warn "No entry for '$VPS_HOST' found in known_hosts (nothing to remove)."
    else
        _info "No known_hosts file yet — nothing to clean up."
    fi

    # ------------------------------------------------------------
    # 5. Print public key + copy-to-VPS instructions
    # ------------------------------------------------------------
    _heading "Your public key"
    echo ""
    cat "$PUB_FILE"
    echo ""
    echo "  ─────────────────────────────────────────────────────────"
    echo "  Add this key to your VPS by running ONE of the following:"
    echo ""
    echo "  Option A – ssh-copy-id (easiest, requires password login):"
    echo "    ssh-copy-id -i $PUB_FILE <user>@$VPS_HOST"
    echo ""
    echo "  Option B – manual (if you have console/root access):"
    echo "    On the VPS, run:"
    echo "      mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    echo "      echo '<paste public key above>' >> ~/.ssh/authorized_keys"
    echo "      chmod 600 ~/.ssh/authorized_keys"
    echo "  ─────────────────────────────────────────────────────────"
    echo ""
    echo "  Then connect with:"
    echo "    ssh -i $KEY_FILE <user>@$VPS_HOST"
else
    # Still print the public key even if no host was provided
    _heading "Your public key (copy this to ~/.ssh/authorized_keys on your VPS)"
    echo ""
    cat "$PUB_FILE"
    echo ""
    echo "  When you know your VPS address, run:"
    echo "    ssh-copy-id -i $PUB_FILE <user>@<your-vps-ip>"
    echo "  or re-run this script and enter the VPS hostname/IP."
fi

# ------------------------------------------------------------
# Done
# ------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    SSH setup complete!                    ║"
echo "╚══════════════════════════════════════════╝"
echo "  Key : $KEY_FILE"
echo "  Pub : $PUB_FILE"
echo ""
