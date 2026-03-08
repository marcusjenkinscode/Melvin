#!/bin/bash
# ============================================================
# setup.sh – one-shot Ubuntu / Linux setup for Melvin
# ============================================================
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Melvin – Ubuntu Setup                 ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ------------------------------------------------------------
# 1. Update apt packages
# ------------------------------------------------------------
echo "▶  Updating package list…"
sudo apt-get update -y && sudo apt-get upgrade -y

# ------------------------------------------------------------
# 2. Install system deps
# ------------------------------------------------------------
echo ""
echo "▶  Installing system packages…"
sudo apt-get install -y python3 python3-pip build-essential libffi-dev libssl-dev git curl

# ------------------------------------------------------------
# 3. Install Python deps
# ------------------------------------------------------------
echo ""
echo "▶  Installing Python dependencies…"
pip3 install --upgrade pip --user
pip3 install --user -r requirements.txt

# ------------------------------------------------------------
# 4. Install Ollama
# ------------------------------------------------------------
echo ""
echo "▶  Installing Ollama…"

ARCH="$(uname -m)"
case "$ARCH" in
    aarch64 | arm64)
        OLLAMA_TARBALL="ollama-linux-arm64"
        ;;
    armv7l | armhf)
        OLLAMA_TARBALL="ollama-linux-arm"
        ;;
    x86_64)
        OLLAMA_TARBALL="ollama-linux-amd64"
        ;;
    *)
        echo "  [!] Unsupported architecture: $ARCH"
        echo "  Please install Ollama manually from https://ollama.com"
        OLLAMA_TARBALL=""
        ;;
esac

if [ -n "$OLLAMA_TARBALL" ]; then
    OLLAMA_URL="https://github.com/ollama/ollama/releases/latest/download/${OLLAMA_TARBALL}.tgz"
    INSTALL_DIR="/usr/local/bin"

    echo "  Downloading $OLLAMA_TARBALL…"
    curl -fsSL "$OLLAMA_URL" | tar -xz -C /tmp
    if sudo mv /tmp/ollama "$INSTALL_DIR/ollama"; then
        sudo chmod +x "$INSTALL_DIR/ollama"
        echo "  Ollama installed → $INSTALL_DIR/ollama"
    else
        echo "  [!] Failed to move Ollama binary to $INSTALL_DIR."
        echo "      Try:  mv /tmp/ollama $INSTALL_DIR/ollama"
        OLLAMA_TARBALL=""
    fi
fi

# ------------------------------------------------------------
# 5. Pull a default model
# ------------------------------------------------------------
echo ""
echo "▶  Starting Ollama server in the background…"
ollama serve &>/tmp/ollama_setup.log &
OLLAMA_PID=$!

# Wait until Ollama is accepting connections (up to 30 s)
echo -n "  Waiting for Ollama to become ready"
READY=0
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        READY=1
        break
    fi
    echo -n "."
    sleep 1
done
echo ""
if [ "$READY" -ne 1 ]; then
    echo "  [!] Ollama did not start within 30 seconds."
    echo "      Check /tmp/ollama_setup.log for details."
    echo "      You can start it manually later: ollama serve &"
fi

# Try to pull the smallest capable model
MODELS=("phi3:mini" "gemma2:2b" "llama3.2:3b")
PULLED=""
for MODEL in "${MODELS[@]}"; do
    echo "  Pulling $MODEL (this may take several minutes on first run)…"
    if ollama pull "$MODEL" 2>&1; then
        PULLED="$MODEL"
        break
    fi
done

if [ -z "$PULLED" ]; then
    echo ""
    echo "  [!] Could not automatically pull a model."
    echo "      After setup, run:  ollama pull phi3:mini"
fi

# Keep Ollama running (don't kill $OLLAMA_PID so it stays up)

# ------------------------------------------------------------
# 6. Done
# ------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║    Setup complete!                        ║"
echo "╠══════════════════════════════════════════╣"
if [ -n "$PULLED" ]; then
    echo "║  Model pulled : $PULLED"
fi
echo "║"
echo "║  To start Melvin:"
echo "║    ollama serve &    # (if not already running)"
echo "║    python3 melvin.py"
echo "╚══════════════════════════════════════════╝"
echo ""
