# Melvin 🤖

A local, private LLM chatbot that:

* **runs completely offline** – powered by [Ollama](https://ollama.com) and the best free open-source models
* **learns from every conversation** – after every 100 prompts the key points of your chat are automatically extracted by the model itself, compressed with `zlib`, and encrypted with Fernet (AES-128-CBC + HMAC) before being stored to disk
* **remembers across sessions** – on each start-up Melvin loads all past memory snapshots and feeds the key points back into the model as context
* **works on Android / Termux** – designed for ARM64 devices with limited RAM; defaults to `phi3:mini` (≈2.3 GB)

---

## Quick start – Linux / macOS

```bash
# 1. Install Ollama  (https://ollama.com/download)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model (one-time download)
ollama pull phi3:mini      # ~2.3 GB, very capable

# 3. Start the Ollama server (in a separate terminal or background)
ollama serve &

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Chat!
python melvin.py
```

---

## Quick start – Termux (Android)

```bash
# Clone this repo inside Termux, then:
chmod +x setup.sh
./setup.sh          # installs Ollama, Python deps, and pulls phi3:mini

# After setup completes:
ollama serve &
python melvin.py
```

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
python melvin.py
```

---

## Project structure

```
melvin.py           # Main chatbot – Ollama API, REPL, snapshot trigger
memory_manager.py   # MemoryChunk read/write, encryption, file rolling
config.py           # All tunable settings in one place
requirements.txt    # Python dependencies
setup.sh            # One-shot Termux/Android setup script
tests/
  test_memory_manager.py   # Unit tests (no Ollama needed)
  test_melvin.py           # Unit tests with mocked HTTP
```
