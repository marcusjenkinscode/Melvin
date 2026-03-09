# Melvin 🤖

A local, private LLM chatbot that:

* **runs completely offline** – powered by [Ollama](https://ollama.com) and the best free open-source models
* **learns from every conversation** – after every 100 prompts the key points of your chat are automatically extracted by the model itself, compressed with `zlib`, and encrypted with AES-128 (Fernet) before being stored to disk
* **remembers across sessions** – on each start-up Melvin loads all past memory snapshots and feeds the key points back into the model as context
* **works on Android / Termux** – designed for ARM64 devices with limited RAM; defaults to `phi3:mini` (≈2.3 GB)

---

## Quick start – Linux / macOS

```bash
# 1. Install Ollama  (https://ollama.com/download)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Clone this repo
git clone https://github.com/marcusjenkinscode/Melvin.git
cd Melvin

# 3. Install Melvin (adds the 'melvin' command)
pip install .

# 4. Run Melvin (Ollama starts automatically if needed)
melvin
```

Melvin will auto-start Ollama if it isn't already running and
interactively offer to download a model when none are installed.

### Running without installing

If you prefer not to install system-wide you can run directly:

```bash
pip install -r requirements.txt
python melvin.py
```

---

## Quick start – Ubuntu / Linux

```bash
# Clone this repo, then:
chmod +x setup.sh
./setup.sh          # installs Ollama, Python deps, and pulls phi3:mini

# After setup completes:
ollama serve &
python3 melvin.py
```

---

## Quick start – Termux (Android)

> **Note:** `setup.sh` targets Ubuntu/Linux. For Termux, follow the manual steps below using `pkg` instead of `apt-get`.

```bash
# Inside Termux:
pkg update -y && pkg upgrade -y
pkg install -y python python-pip clang libffi openssl git curl

pip install -r requirements.txt

# Install Ollama manually from https://ollama.com, then:
ollama serve &
python melvin.py
melvin              # if you chose the system-wide install
python melvin.py    # otherwise
```

The setup script will ask whether you want to install the `melvin`
command system-wide.  You can always do this later with `pip install .`.

---

## Chat commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/memory` | Show recalled key points from past sessions |
| `/snapshot` | Force a memory snapshot right now |
| `/clear` | Clear current conversation (saved memory is kept) |
| `/model` | Show the active model |
| `/models` | List all locally available Ollama models |
| `/quit` | Exit Melvin (offers to snapshot unsaved turns) |

---

## Memory storage

| File | Purpose |
|------|---------|
| `MemoryChunk.json` | Encrypted conversation snapshots (auto-created) |
| `MemoryChunk2.json` | Created automatically when the first file reaches 1 GB |
| `melvin.key` | Your Fernet encryption key – **back this up!** |

Each entry in a `MemoryChunk` file stores only a `base64url`-encoded,
`zlib`-compressed, Fernet-encrypted blob.  The plaintext never touches disk.

---

## Recommended models (best for mobile)

| Model | Size | Notes |
|-------|------|-------|
| `phi3:mini` | 2.3 GB | Default – Microsoft Phi-3, very smart |
| `llama3.2:3b` | 2.0 GB | Meta's latest small model |
| `qwen2.5:3b` | 1.9 GB | Alibaba's efficient model |
| `gemma2:2b` | 1.6 GB | Google Gemma 2, lightest option |
| `mistral:7b` | 4.1 GB | If your device has ≥6 GB RAM |

To switch models, pull the one you want and restart Melvin:

```bash
ollama pull gemma2:2b
melvin
```

---

## Project structure

```
melvin.py           # Main chatbot – Ollama API, REPL, snapshot trigger
memory_manager.py   # MemoryChunk read/write, encryption, file rolling
config.py           # All tunable settings in one place
pyproject.toml      # Python packaging (pip install .)
requirements.txt    # Python dependencies
setup.sh            # One-shot Ubuntu/Linux setup script
tests/
  test_memory_manager.py   # Unit tests (no Ollama needed)
  test_melvin.py           # Unit tests with mocked HTTP
```
