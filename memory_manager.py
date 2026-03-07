"""
memory_manager.py – persistent, encrypted conversation memory for Melvin.

Storage layout
--------------
Each MemoryChunk*.json file has this top-level structure:

    {
        "version": "1.0",
        "chunks": [
            {
                "id":           <int>,
                "timestamp":    "<ISO-8601>",
                "prompt_range": [<start>, <end>],
                "data":         "<Fernet token (URL-safe base64)>"
            },
            ...
        ]
    }

The "data" field is a Fernet token (URL-safe base64 string).  Decrypting it
yields zlib-compressed UTF-8 JSON with the following structure:

    {
        "key_points":            ["..."],
        "conversation_summary":  [{"role": "...", "content": "..."}, ...]
    }

Encryption key
--------------
A single 32-byte Fernet key is stored in `melvin.key` (path configured in
config.py).  The file is created with owner-read/write-only permissions
(0o600).  Keep this file safe – without it the chunks cannot be decrypted.

Encryption algorithm
--------------------
Fernet uses AES-128-CBC + HMAC-SHA256.

File rolling
------------
When a MemoryChunk file would exceed MEMORY_CHUNK_MAX_BYTES after a new write,
Melvin automatically starts a new numbered file:
    MemoryChunk.json → MemoryChunk2.json → MemoryChunk3.json → …
"""

from __future__ import annotations

import base64
import json
import os
import time
import zlib
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

import config


class MemoryManager:
    """Manages reading and writing of encrypted MemoryChunk files."""

    # ------------------------------------------------------------------
    # Construction & key management
    # ------------------------------------------------------------------

    def __init__(
        self,
        memory_dir: str = config.MEMORY_DIR,
        key_file: str = config.KEY_FILE,
        max_chunk_bytes: int = config.MEMORY_CHUNK_MAX_BYTES,
        basename: str = config.MEMORY_CHUNK_BASENAME,
    ) -> None:
        self.memory_dir = Path(memory_dir)
        self.key_path = self.memory_dir / key_file
        self.max_chunk_bytes = max_chunk_bytes
        self.basename = basename

        # Ensure the memory directory exists before attempting key I/O
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._key = self._load_or_create_key()
        self._fernet = Fernet(self._key)

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _load_or_create_key(self) -> bytes:
        """Return the existing Fernet key or generate (and persist) a new one.

        The key file is created with owner-read/write-only permissions (0o600)
        to prevent other local users from reading it on multi-user systems.
        """
        if self.key_path.exists():
            return self.key_path.read_bytes()
        key = Fernet.generate_key()
        # Create with restrictive permissions: owner read/write only
        fd = os.open(str(self.key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(key)
        return key

    # ------------------------------------------------------------------
    # Encryption / compression helpers
    # ------------------------------------------------------------------

    def _pack(self, payload: dict[str, Any]) -> str:
        """Serialize *payload* -> JSON -> zlib-compress -> Fernet-encrypt (URL-safe token)."""
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        compressed = zlib.compress(raw, level=9)
        encrypted = self._fernet.encrypt(compressed)
        return encrypted.decode("ascii")

    def _unpack(self, encoded: str) -> dict[str, Any]:
        """Reverse of :meth:`_pack`.

        Supports both the current direct-Fernet-token format and the legacy
        double-base64-encoded format for backward compatibility.
        """
        token = encoded.encode("ascii")
        try:
            # Preferred path: encoded is the Fernet token itself.
            compressed = self._fernet.decrypt(token)
        except InvalidToken:
            # Backward compatibility: encoded is base64(Fernet token).
            encrypted = base64.urlsafe_b64decode(token)
            compressed = self._fernet.decrypt(encrypted)
        raw = zlib.decompress(compressed)
        return json.loads(raw.decode("utf-8"))

    # ------------------------------------------------------------------
    # File selection
    # ------------------------------------------------------------------

    def _chunk_path(self, index: int) -> Path:
        """Return the Path for chunk file number *index* (1-based)."""
        name = (
            f"{self.basename}.json"
            if index == 1
            else f"{self.basename}{index}.json"
        )
        return self.memory_dir / name

    def _current_chunk_path(self, new_entry_bytes: int = 0) -> Path:
        """
        Return the chunk file that should receive the next entry.

        Walks the numbered sequence until it finds a file that either
        does not exist yet or would still be under the size limit after
        the new entry (*new_entry_bytes*) is appended.
        """
        index = 1
        while True:
            path = self._chunk_path(index)
            if not path.exists():
                return path
            if path.stat().st_size + new_entry_bytes < self.max_chunk_bytes:
                return path
            index += 1

    # ------------------------------------------------------------------
    # Low-level read / write
    # ------------------------------------------------------------------

    def _load_chunk_file(self, path: Path) -> dict[str, Any]:
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        return {"version": "1.0", "chunks": []}

    def _save_chunk_file(self, path: Path, data: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_memory(
        self,
        conversation: list[dict[str, str]],
        key_points: list[str],
        prompt_range: tuple[int, int],
    ) -> Path:
        """
        Compress, encrypt, and append a memory snapshot.

        Parameters
        ----------
        conversation:
            List of ``{"role": ..., "content": ...}`` dicts for the window
            being archived.
        key_points:
            Human-readable bullet-point summary extracted by the LLM.
        prompt_range:
            ``(first_prompt_number, last_prompt_number)`` covered by this
            snapshot.

        Returns
        -------
        Path
            The MemoryChunk file that was written to.
        """
        payload = {
            "key_points": key_points,
            "conversation_summary": conversation,
        }
        packed = self._pack(payload)

        # Estimate bytes the new entry will add (packed string + JSON wrapper overhead)
        estimated_new_bytes = len(packed.encode("utf-8")) + 256
        chunk_path = self._current_chunk_path(estimated_new_bytes)
        chunk_data = self._load_chunk_file(chunk_path)

        chunk_data["chunks"].append(
            {
                "id": len(chunk_data["chunks"]) + 1,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "prompt_range": list(prompt_range),
                "data": packed,
            }
        )

        self._save_chunk_file(chunk_path, chunk_data)
        return chunk_path

    def load_all_key_points(self) -> list[dict[str, Any]]:
        """
        Read every MemoryChunk file and return the decrypted key-point lists.

        Each returned item is::

            {
                "timestamp":    "<ISO-8601>",
                "prompt_range": [start, end],
                "key_points":   ["...", ...]
            }

        Corrupted or unreadable entries are silently skipped.
        """
        results: list[dict[str, Any]] = []
        index = 1
        while True:
            path = self._chunk_path(index)
            if not path.exists():
                break
            try:
                chunk_file = self._load_chunk_file(path)
                for entry in chunk_file.get("chunks", []):
                    try:
                        payload = self._unpack(entry["data"])
                        results.append(
                            {
                                "timestamp": entry.get("timestamp", ""),
                                "prompt_range": entry.get("prompt_range", []),
                                "key_points": payload.get("key_points", []),
                            }
                        )
                    except Exception:
                        pass  # skip corrupted individual entries
            except Exception:
                pass  # skip corrupted files
            index += 1
        return results

    def list_chunk_files(self) -> list[Path]:
        """Return all existing MemoryChunk file paths in order."""
        paths: list[Path] = []
        index = 1
        while True:
            path = self._chunk_path(index)
            if not path.exists():
                break
            paths.append(path)
            index += 1
        return paths

    def chunk_count(self) -> int:
        """Return the total number of saved memory snapshots across all files."""
        total = 0
        for path in self.list_chunk_files():
            try:
                data = self._load_chunk_file(path)
                total += len(data.get("chunks", []))
            except Exception:
                pass
        return total
