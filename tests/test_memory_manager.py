"""
tests/test_memory_manager.py

Unit tests for MemoryManager – encryption, compression, rolling files, and
key-point retrieval.  These tests run entirely in a temporary directory and
do NOT require Ollama or any network access.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the repo root is on sys.path so we can import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.fernet import InvalidToken

from memory_manager import MemoryManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_manager(tmp_path):
    """Return a MemoryManager backed by a fresh temporary directory."""
    return MemoryManager(
        memory_dir=str(tmp_path),
        key_file="test.key",
        max_chunk_bytes=1 * 1024 * 1024 * 1024,  # 1 GB (default)
        basename="MemoryChunk",
    )


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

class TestKeyManagement:
    def test_key_file_created_on_first_use(self, tmp_path):
        MemoryManager(memory_dir=str(tmp_path), key_file="k.key")
        assert (tmp_path / "k.key").exists()

    def test_key_file_reused_on_second_instantiation(self, tmp_path):
        MemoryManager(memory_dir=str(tmp_path), key_file="k.key")
        key1 = (tmp_path / "k.key").read_bytes()

        MemoryManager(memory_dir=str(tmp_path), key_file="k.key")
        key2 = (tmp_path / "k.key").read_bytes()

        assert key1 == key2

    def test_key_is_32_bytes_fernet_format(self, tmp_path):
        import base64
        MemoryManager(memory_dir=str(tmp_path), key_file="k.key")
        raw = (tmp_path / "k.key").read_bytes()
        decoded = base64.urlsafe_b64decode(raw)
        assert len(decoded) == 32


# ---------------------------------------------------------------------------
# Pack / unpack round-trip
# ---------------------------------------------------------------------------

class TestPackUnpack:
    def test_roundtrip_simple(self, tmp_manager):
        payload = {"hello": "world", "nums": [1, 2, 3]}
        packed   = tmp_manager._pack(payload)
        unpacked = tmp_manager._unpack(packed)
        assert unpacked == payload

    def test_roundtrip_unicode(self, tmp_manager):
        payload = {"text": "こんにちは 🌍"}
        assert tmp_manager._unpack(tmp_manager._pack(payload)) == payload

    def test_packed_is_not_plaintext(self, tmp_manager):
        payload = {"secret": "s3cr3t_value"}
        packed = tmp_manager._pack(payload)
        assert "s3cr3t_value" not in packed

    def test_wrong_key_raises(self, tmp_path):
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        mgr1 = MemoryManager(memory_dir=str(dir_a), key_file="k.key")
        packed = mgr1._pack({"x": 1})

        mgr2 = MemoryManager(memory_dir=str(dir_b), key_file="k.key")
        with pytest.raises(InvalidToken):
            mgr2._unpack(packed)


# ---------------------------------------------------------------------------
# save_memory / load_all_key_points
# ---------------------------------------------------------------------------

class TestSaveAndLoad:
    def test_save_creates_chunk_file(self, tmp_manager, tmp_path):
        tmp_manager.save_memory(
            conversation=[{"role": "user", "content": "hi"}],
            key_points=["greeting"],
            prompt_range=(1, 1),
        )
        assert (tmp_path / "MemoryChunk.json").exists()

    def test_saved_file_is_valid_json(self, tmp_manager, tmp_path):
        tmp_manager.save_memory(
            conversation=[],
            key_points=["test point"],
            prompt_range=(1, 100),
        )
        data = json.loads((tmp_path / "MemoryChunk.json").read_text())
        assert data["version"] == "1.0"
        assert len(data["chunks"]) == 1

    def test_load_key_points_returns_correct_data(self, tmp_manager):
        points = ["The user likes Python", "prefers dark mode"]
        tmp_manager.save_memory(
            conversation=[{"role": "user", "content": "hello"}],
            key_points=points,
            prompt_range=(1, 100),
        )
        loaded = tmp_manager.load_all_key_points()
        assert len(loaded) == 1
        assert loaded[0]["key_points"] == points

    def test_multiple_saves_accumulate_chunks(self, tmp_manager, tmp_path):
        for i in range(3):
            tmp_manager.save_memory(
                conversation=[],
                key_points=[f"point {i}"],
                prompt_range=(i * 100, i * 100 + 99),
            )
        data = json.loads((tmp_path / "MemoryChunk.json").read_text())
        assert len(data["chunks"]) == 3

    def test_chunk_count(self, tmp_manager):
        for i in range(5):
            tmp_manager.save_memory([], [f"p{i}"], (i, i))
        assert tmp_manager.chunk_count() == 5

    def test_prompt_range_stored_correctly(self, tmp_manager):
        tmp_manager.save_memory([], ["point"], (42, 141))
        loaded = tmp_manager.load_all_key_points()
        assert loaded[0]["prompt_range"] == [42, 141]


# ---------------------------------------------------------------------------
# File rolling (size cap)
# ---------------------------------------------------------------------------

class TestFileRolling:
    def test_rolls_to_second_file_when_first_is_at_limit(self, tmp_path):
        # Set a tiny cap so we trigger a rollover after the first save
        mgr = MemoryManager(
            memory_dir=str(tmp_path),
            key_file="k.key",
            max_chunk_bytes=1,   # 1 byte – guaranteed to overflow after first write
        )
        mgr.save_memory([], ["first"], (1, 1))
        mgr.save_memory([], ["second"], (2, 2))

        assert (tmp_path / "MemoryChunk.json").exists()
        assert (tmp_path / "MemoryChunk2.json").exists()

    def test_loads_from_both_files(self, tmp_path):
        mgr = MemoryManager(
            memory_dir=str(tmp_path),
            key_file="k.key",
            max_chunk_bytes=1,
        )
        mgr.save_memory([], ["from file 1"], (1, 1))
        mgr.save_memory([], ["from file 2"], (2, 2))

        points = mgr.load_all_key_points()
        all_kp = [kp for p in points for kp in p["key_points"]]
        assert "from file 1" in all_kp
        assert "from file 2" in all_kp

    def test_rolls_to_third_file(self, tmp_path):
        mgr = MemoryManager(
            memory_dir=str(tmp_path),
            key_file="k.key",
            max_chunk_bytes=1,
        )
        for i in range(3):
            mgr.save_memory([], [f"p{i}"], (i, i))

        assert (tmp_path / "MemoryChunk3.json").exists()

    def test_list_chunk_files(self, tmp_path):
        mgr = MemoryManager(
            memory_dir=str(tmp_path),
            key_file="k.key",
            max_chunk_bytes=1,
        )
        for i in range(3):
            mgr.save_memory([], [f"p{i}"], (i, i))

        files = mgr.list_chunk_files()
        names = [f.name for f in files]
        assert names == [
            "MemoryChunk.json",
            "MemoryChunk2.json",
            "MemoryChunk3.json",
        ]


# ---------------------------------------------------------------------------
# Resilience – corrupted data is skipped, not fatal
# ---------------------------------------------------------------------------

class TestResilience:
    def test_corrupted_entry_skipped(self, tmp_path):
        mgr = MemoryManager(memory_dir=str(tmp_path), key_file="k.key")

        # Write one good entry
        mgr.save_memory([], ["good point"], (1, 1))

        # Manually corrupt the data field
        chunk_file = tmp_path / "MemoryChunk.json"
        data = json.loads(chunk_file.read_text())
        data["chunks"][0]["data"] = "this_is_not_valid_base64_or_fernet!!!"
        chunk_file.write_text(json.dumps(data))

        # Should not raise; the corrupted entry is silently skipped
        points = mgr.load_all_key_points()
        assert points == []

    def test_empty_directory_returns_empty_list(self, tmp_manager):
        assert tmp_manager.load_all_key_points() == []
        assert tmp_manager.chunk_count() == 0
        assert tmp_manager.list_chunk_files() == []
