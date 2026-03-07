"""
tests/test_melvin.py

Unit tests for melvin.py helper functions.
All Ollama HTTP calls are mocked – no real server is needed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import melvin


# ---------------------------------------------------------------------------
# _ollama_tags
# ---------------------------------------------------------------------------

class TestOllamaTags:
    def test_returns_model_names(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [{"name": "phi3:mini"}, {"name": "llama3.2:3b"}]
        }
        with patch("melvin.requests.get", return_value=mock_resp):
            tags = melvin._ollama_tags()
        assert tags == ["phi3:mini", "llama3.2:3b"]

    def test_returns_empty_on_connection_error(self):
        with patch("melvin.requests.get", side_effect=ConnectionError):
            tags = melvin._ollama_tags()
        assert tags == []

    def test_returns_empty_on_malformed_response(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}   # no "models" key
        with patch("melvin.requests.get", return_value=mock_resp):
            tags = melvin._ollama_tags()
        assert tags == []


# ---------------------------------------------------------------------------
# _choose_model
# ---------------------------------------------------------------------------

class TestChooseModel:
    def test_returns_first_preferred_when_available(self):
        with patch("melvin._ollama_tags", return_value=["phi3:mini", "llama3.2:3b"]):
            assert melvin._choose_model() == "phi3:mini"

    def test_falls_through_to_next_preferred(self):
        with patch("melvin._ollama_tags", return_value=["llama3.2:3b"]):
            assert melvin._choose_model() == "llama3.2:3b"

    def test_falls_back_to_first_available_when_none_preferred(self):
        with patch("melvin._ollama_tags", return_value=["some-other-model:latest"]):
            assert melvin._choose_model() == "some-other-model:latest"

    def test_returns_none_when_no_models(self):
        with patch("melvin._ollama_tags", return_value=[]):
            assert melvin._choose_model() is None


# ---------------------------------------------------------------------------
# _extract_key_points
# ---------------------------------------------------------------------------

class TestExtractKeyPoints:
    def _make_chat_mock(self, response: str):
        return patch("melvin._chat", return_value=response)

    def test_parses_valid_json_array(self):
        response = '["User likes Python", "Prefers dark mode"]'
        with self._make_chat_mock(response):
            points = melvin._extract_key_points("phi3:mini", [])
        assert points == ["User likes Python", "Prefers dark mode"]

    def test_parses_json_array_embedded_in_text(self):
        response = 'Sure! Here are the key points:\n["Point A", "Point B"]'
        with self._make_chat_mock(response):
            points = melvin._extract_key_points("phi3:mini", [])
        assert points == ["Point A", "Point B"]

    def test_falls_back_to_raw_text_when_not_json(self):
        response = "Just a plain text response"
        with self._make_chat_mock(response):
            points = melvin._extract_key_points("phi3:mini", [])
        assert points == ["(no key points extracted)"]

    def test_returns_fallback_for_empty_response(self):
        with self._make_chat_mock(""):
            points = melvin._extract_key_points("phi3:mini", [])
        assert points == ["(no key points extracted)"]

    def test_returns_fallback_for_error_response(self):
        response = "[Error] Could not reach Ollama. Make sure it is running: ollama serve"
        with self._make_chat_mock(response):
            points = melvin._extract_key_points("phi3:mini", [])
        assert points == ["(no key points extracted)"]


# ---------------------------------------------------------------------------
# MelvinChat._build_context
# ---------------------------------------------------------------------------

class TestBuildContext:
    def _make_chat(self, tmp_path, memories=None):
        chat = melvin.MelvinChat()
        chat.memory = MagicMock()
        chat.memory.load_all_key_points.return_value = memories or []
        chat.model = "phi3:mini"
        return chat

    def test_system_prompt_always_first(self, tmp_path):
        chat = self._make_chat(tmp_path)
        ctx = chat._build_context()
        assert ctx[0]["role"] == "system"

    def test_memory_injected_when_present(self, tmp_path):
        memories = [{"key_points": ["User is a Python dev"], "prompt_range": [1, 100], "timestamp": "2024-01-01"}]
        chat = self._make_chat(tmp_path, memories=memories)
        ctx = chat._build_context()
        # System prompt only; memory is injected as assistant role
        roles = [m["role"] for m in ctx]
        assert roles.count("system") == 1
        assert "assistant" in roles
        combined = " ".join(m["content"] for m in ctx)
        assert "User is a Python dev" in combined

    def test_no_memory_injection_when_empty(self, tmp_path):
        chat = self._make_chat(tmp_path)
        ctx = chat._build_context()
        assert len([m for m in ctx if m["role"] == "system"]) == 1

    def test_recent_history_appended(self, tmp_path):
        chat = self._make_chat(tmp_path)
        chat.history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        ctx = chat._build_context()
        contents = [m["content"] for m in ctx]
        assert "hello" in contents
        assert "hi there" in contents
