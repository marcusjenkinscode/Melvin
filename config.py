"""
Melvin – configuration settings.
All tuneable knobs live here so the rest of the code stays clean.
"""

# ---------------------------------------------------------------------------
# Ollama endpoint (change if Ollama is bound to a different host/port)
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = "http://localhost:11434"

# ---------------------------------------------------------------------------
# Model preference order – Melvin tries each in turn until one is available.
# All are free, open-source, and run comfortably on Android/Termux hardware.
#
#   phi3:mini      – 2.3 GB  Microsoft Phi-3 Mini;  very capable, tiny RAM
#   llama3.2:3b    – 2.0 GB  Meta's latest small model
#   qwen2.5:3b     – 1.9 GB  Alibaba's efficient model
#   gemma2:2b      – 1.6 GB  Google Gemma 2 – lightest choice
#   mistral:7b     – 4.1 GB  Mistral 7B – if you have the RAM
# ---------------------------------------------------------------------------
PREFERRED_MODELS = [
    "phi3:mini",
    "llama3.2:3b",
    "qwen2.5:3b",
    "gemma2:2b",
    "mistral:7b",
]

# Fall back to this name when none of the preferred models respond
DEFAULT_MODEL = PREFERRED_MODELS[0]

# ---------------------------------------------------------------------------
# Memory / MemoryChunk settings
# ---------------------------------------------------------------------------

# Number of user prompts between automatic memory snapshots
MEMORY_SNAPSHOT_INTERVAL = 100

# Maximum size (bytes) of a single MemoryChunk file before rolling over
MEMORY_CHUNK_MAX_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB

# Directory where MemoryChunk files and the encryption key are stored
MEMORY_DIR = "."

# Filename for the symmetric encryption key
KEY_FILE = "melvin.key"

# Base name for memory chunk files (MemoryChunk.json, MemoryChunk2.json, …)
MEMORY_CHUNK_BASENAME = "MemoryChunk"

# ---------------------------------------------------------------------------
# Chat behaviour
# ---------------------------------------------------------------------------

# How many recent conversation turns to send as context to the model
MAX_CONTEXT_TURNS = 20

# System prompt that shapes Melvin's personality
SYSTEM_PROMPT = (
    "You are Melvin, a helpful, knowledgeable, and concise AI assistant. "
    "You remember important information from past conversations and use it "
    "to give personalised, context-aware answers. "
    "When you don't know something, say so clearly."
)
