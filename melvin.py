#!/usr/bin/env python3
"""
melvin.py – local LLM chatbot with persistent encrypted memory.

Quick-start (Termux / Linux)
-----------------------------
1.  Install Ollama and pull a model:
        ollama pull phi3:mini
2.  Install Python deps:
        pip install -r requirements.txt
3.  Run Melvin:
        python melvin.py

Type  /help  inside the chat to see available commands.
"""

from __future__ import annotations

import json
import sys
import textwrap
from typing import Any

import requests

import config
from memory_manager import MemoryManager

# ---------------------------------------------------------------------------
# Terminal colour helpers (gracefully degrade when colours aren't supported)
# ---------------------------------------------------------------------------

try:
    import shutil
    _COLS = shutil.get_terminal_size(fallback=(80, 24)).columns
except Exception:
    _COLS = 80

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_CYAN   = "\033[36m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_DIM    = "\033[2m"


def _c(code: str, text: str) -> str:
    """Wrap *text* in an ANSI colour code (no-op on non-TTY)."""
    if sys.stdout.isatty():
        return f"{code}{text}{_RESET}"
    return text


def _hr(char: str = "─") -> str:
    return _c(_DIM, char * min(_COLS, 78))


# ---------------------------------------------------------------------------
# Ollama API helpers
# ---------------------------------------------------------------------------

def _ollama_tags() -> list[str]:
    """Return names of locally available Ollama models, or [] on error."""
    try:
        r = requests.get(
            f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5
        )
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def _choose_model() -> str | None:
    """
    Try each model in PREFERRED_MODELS; return the first that is available
    locally, or *None* if none are found.
    """
    available = _ollama_tags()
    if not available:
        return None
    available_lower = {m.lower() for m in available}
    for candidate in config.PREFERRED_MODELS:
        # Accept partial name match (e.g. "phi3:mini" matches "phi3:mini-128k")
        for name in available:
            if name.lower().startswith(candidate.lower()):
                return name
    # Fall back to the first available model
    return available[0] if available else None


def _chat(
    model: str,
    messages: list[dict[str, str]],
    stream: bool = True,
) -> str:
    """
    Send *messages* to Ollama's /api/chat endpoint and return the
    complete assistant reply as a string.

    When *stream* is True the reply is printed to stdout character-by-character
    as it arrives (giving a "typing" effect).
    """
    url = f"{config.OLLAMA_BASE_URL}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }

    response_text = ""
    try:
        with requests.post(url, json=payload, stream=stream, timeout=300) as resp:
            resp.raise_for_status()
            if stream:
                print(_c(_GREEN, _BOLD + "Melvin: ") + _RESET, end="", flush=True)
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    chunk = json.loads(raw_line)
                    delta = chunk.get("message", {}).get("content", "")
                    print(delta, end="", flush=True)
                    response_text += delta
                    if chunk.get("done"):
                        break
                print()  # newline after streamed reply
            else:
                data = resp.json()
                response_text = data["message"]["content"]
    except requests.exceptions.ConnectionError:
        response_text = (
            "[Error] Could not reach Ollama. "
            "Make sure it is running: ollama serve"
        )
    except Exception as exc:
        response_text = f"[Error] {exc}"

    return response_text


def _extract_key_points(
    model: str,
    conversation: list[dict[str, str]],
) -> list[str]:
    """
    Ask the model to extract key points from *conversation*.
    Returns a list of bullet-point strings.
    """
    text_repr = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in conversation
        if m["role"] != "system"
    )
    prompt = (
        "Please read the following conversation and extract the most important "
        "facts, decisions, preferences, and topics discussed. "
        "Return ONLY a JSON array of short strings (one per key point), "
        "with no additional text.\n\n"
        f"CONVERSATION:\n{text_repr}"
    )
    raw = _chat(model, [{"role": "user", "content": prompt}], stream=False)

    # Try to parse the JSON array; fall back to a single-item list
    try:
        start = raw.index("[")
        end   = raw.rindex("]") + 1
        points = json.loads(raw[start:end])
        if isinstance(points, list):
            return [str(p) for p in points]
    except Exception:
        pass
    return [raw.strip()] if raw.strip() else ["(no key points extracted)"]


# ---------------------------------------------------------------------------
# Chat session
# ---------------------------------------------------------------------------

class MelvinChat:
    """Manages one interactive chat session."""

    def __init__(self) -> None:
        self.memory = MemoryManager()
        self.model: str | None = None
        self.history: list[dict[str, str]] = []   # full session history
        self.prompt_count: int = 0                 # user turns this session
        self._last_snapshot_at: int = 0            # prompt_count at last snapshot

    # ------------------------------------------------------------------
    # Start-up
    # ------------------------------------------------------------------

    def _print_banner(self) -> None:
        print()
        print(_c(_CYAN, _BOLD + "╔══════════════════════════════════════════╗"))
        print(_c(_CYAN, _BOLD + "║          M E L V I N  🤖                 ║"))
        print(_c(_CYAN, _BOLD + "║  Local LLM  ·  Encrypted Memory          ║"))
        print(_c(_CYAN, _BOLD + "╚══════════════════════════════════════════╝"))
        print()

    def _build_context(self) -> list[dict[str, str]]:
        """
        Build the message list sent to Ollama:
        system prompt → recalled memory → recent conversation turns.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": config.SYSTEM_PROMPT}
        ]

        # Inject recalled key points as an assistant-side memory preamble
        all_memories = self.memory.load_all_key_points()
        if all_memories:
            memory_text = "KEY POINTS FROM PREVIOUS CONVERSATIONS:\n"
            for m in all_memories:
                for point in m["key_points"]:
                    memory_text += f"• {point}\n"
            messages.append(
                {
                    "role": "system",
                    "content": memory_text,
                }
            )

        # Most recent turns (keep context window manageable)
        recent = self.history[-config.MAX_CONTEXT_TURNS * 2:]
        messages.extend(recent)
        return messages

    def start(self) -> None:
        """Entry point – initialise and run the REPL."""
        self._print_banner()

        # Find a usable model
        print(_c(_YELLOW, "⟳  Connecting to Ollama…"), end="\r")
        self.model = _choose_model()

        if self.model is None:
            print(
                _c(_RED, "✗  Ollama is not reachable or no models are installed.\n")
                + "\nTo install Ollama and pull a model:\n"
                + "  pkg install ollama          # Termux\n"
                + "  ollama pull phi3:mini\n"
                + "  ollama serve\n"
            )
            sys.exit(1)

        print(_c(_GREEN, f"✓  Using model: {self.model}          "))

        # Show memory stats
        n_chunks = self.memory.chunk_count()
        if n_chunks:
            print(_c(_DIM, f"   Loaded {n_chunks} memory snapshot(s) from disk."))

        print(_c(_DIM, "   Type /help for available commands.\n"))
        print(_hr())
        print()

        self._repl()

    # ------------------------------------------------------------------
    # REPL
    # ------------------------------------------------------------------

    def _repl(self) -> None:
        while True:
            try:
                user_input = input(_c(_BOLD + _CYAN, "You: ")).strip()
            except (EOFError, KeyboardInterrupt):
                self._do_quit()
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if self._handle_command(user_input):
                    break
                continue

            self._handle_user_message(user_input)

    def _handle_user_message(self, text: str) -> None:
        self.prompt_count += 1
        self.history.append({"role": "user", "content": text})

        messages = self._build_context()
        reply = _chat(self.model, messages)

        self.history.append({"role": "assistant", "content": reply})
        print()

        # Snapshot every MEMORY_SNAPSHOT_INTERVAL prompts
        if self.prompt_count % config.MEMORY_SNAPSHOT_INTERVAL == 0:
            self._snapshot_memory()

    # ------------------------------------------------------------------
    # Memory snapshot
    # ------------------------------------------------------------------

    def _snapshot_memory(self) -> None:
        """Extract key points and persist the turns since the last snapshot."""
        print(_c(_YELLOW, "\n⟳  Creating memory snapshot…"), flush=True)

        # Only archive turns since the previous snapshot; fall back to the full
        # history if no snapshot has been taken yet (e.g. after /clear).
        turns_since = self.prompt_count - self._last_snapshot_at
        window = self.history[-(turns_since * 2):]  # user+assistant pairs
        key_points = _extract_key_points(self.model, window)

        start = self._last_snapshot_at + 1
        end   = self.prompt_count
        saved_path = self.memory.save_memory(
            conversation=window,
            key_points=key_points,
            prompt_range=(start, end),
        )
        self._last_snapshot_at = self.prompt_count

        print(
            _c(_GREEN, f"✓  Memory snapshot saved → {saved_path.name}  ")
            + _c(_DIM, f"({len(key_points)} key point(s))")
        )
        print()

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    def _handle_command(self, cmd: str) -> bool:
        """
        Process a slash command.  Returns True if the session should end.
        """
        parts = cmd.lower().split()
        name  = parts[0]

        if name in ("/quit", "/exit", "/bye"):
            self._do_quit()
            return True

        elif name == "/help":
            self._do_help()

        elif name == "/memory":
            self._do_memory()

        elif name == "/snapshot":
            if self.history:
                self._snapshot_memory()
            else:
                print(_c(_YELLOW, "  No conversation to snapshot yet.\n"))

        elif name == "/clear":
            self.history.clear()
            self._last_snapshot_at = self.prompt_count
            print(_c(_GREEN, "  Conversation history cleared.\n"))

        elif name == "/model":
            print(_c(_DIM, f"  Active model: {self.model}\n"))

        elif name == "/models":
            self._do_models()

        else:
            print(_c(_RED, f"  Unknown command: {name}  (try /help)\n"))

        return False

    def _do_help(self) -> None:
        help_text = textwrap.dedent(
            f"""
            {_c(_BOLD, 'Available commands')}
              /help       – show this message
              /memory     – show recalled key points from past sessions
              /snapshot   – force a memory snapshot right now
              /clear      – clear current conversation (memory is kept)
              /model      – show the active model
              /models     – list all locally available Ollama models
              /quit       – exit Melvin
            """
        )
        print(help_text)

    def _do_memory(self) -> None:
        memories = self.memory.load_all_key_points()
        if not memories:
            print(_c(_YELLOW, "  No memories stored yet.\n"))
            return
        print(_c(_BOLD, f"\n  Remembered key points ({len(memories)} snapshot(s)):\n"))
        for m in memories:
            ts = m.get("timestamp", "?")
            r  = m.get("prompt_range", [])
            range_str = f"prompts {r[0]}–{r[1]}" if len(r) == 2 else ""
            print(_c(_DIM, f"  [{ts}  {range_str}]"))
            for point in m.get("key_points", []):
                print(f"    • {point}")
        print()

    def _do_models(self) -> None:
        tags = _ollama_tags()
        if not tags:
            print(_c(_YELLOW, "  No models found (is Ollama running?).\n"))
            return
        print(_c(_BOLD, "\n  Locally available models:\n"))
        for tag in tags:
            marker = " ← active" if tag == self.model else ""
            print(f"    {tag}{_c(_DIM, marker)}")
        print()

    def _do_quit(self) -> None:
        # Offer a final snapshot if there are unsaved turns since last snapshot
        unsaved = self.prompt_count - self._last_snapshot_at
        if unsaved and self.history:
            try:
                ans = input(
                    _c(_YELLOW, f"\n  Save a memory snapshot for the last {unsaved} prompt(s)? [Y/n] ")
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"
            if ans in ("", "y", "yes"):
                self._snapshot_memory()

        print(_c(_CYAN, "\n  Goodbye! 👋\n"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    MelvinChat().start()


if __name__ == "__main__":
    main()
