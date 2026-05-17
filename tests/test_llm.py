"""
Tests for backend/llm.py — all Ollama calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.llm import _strip_fences, _parse_debug, generate_code, debug_code


class TestStripFences:
    def test_python_fence(self):
        assert _strip_fences("```python\nprint('hi')\n```") == "print('hi')"

    def test_plain_fence(self):
        assert _strip_fences("```\nx = 1\n```") == "x = 1"

    def test_no_fence_returns_stripped_raw(self):
        assert _strip_fences("  print('hi')  ") == "print('hi')"

    def test_multiline_code_in_fence(self):
        code = "def f():\n    return 1"
        assert _strip_fences(f"```python\n{code}\n```") == code

    def test_empty_fence(self):
        assert _strip_fences("```\n\n```") == ""


class TestParseDebug:
    def test_explanation_and_code_extracted(self):
        text = "Fixed the index error.\n\n```python\nprint('hi')\n```"
        code, explanation = _parse_debug(text)
        assert code == "print('hi')"
        assert "Fixed" in explanation

    def test_no_fence_returns_raw_code(self):
        code, explanation = _parse_debug("print('fixed')")
        assert code == "print('fixed')"
        assert explanation == "Code fixed."

    def test_explanation_capped_at_200_chars(self):
        long_line = "A" * 300
        text = f"{long_line}\n\n```python\npass\n```"
        _, explanation = _parse_debug(text)
        assert len(explanation) <= 200

    def test_no_text_before_fence_uses_default(self):
        text = "```python\nx = 1\n```"
        _, explanation = _parse_debug(text)
        assert explanation == "Code fixed."


class TestGenerateCode:
    def _mock_resp(self, content: str):
        resp = MagicMock()
        resp.message.content = content
        return resp

    def test_returns_stripped_code(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.return_value = self._mock_resp(
                "```python\nprint('hello')\n```"
            )
            result = generate_code("print hello")
        assert result == "print('hello')"

    def test_raw_response_without_fence(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.return_value = self._mock_resp("x = 1")
            result = generate_code("set x to 1")
        assert result == "x = 1"

    def test_ollama_unavailable_raises_runtime_error(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.side_effect = ConnectionError("refused")
            with pytest.raises(RuntimeError, match="Ollama unavailable"):
                generate_code("do something")

    def test_passes_transcript_as_user_message(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.return_value = self._mock_resp("pass")
            generate_code("my transcript")
            call_args = mock_client.return_value.chat.call_args
            messages = call_args.kwargs.get("messages") or call_args.args[1]
            user_msg = next(m for m in messages if m["role"] == "user")
            assert user_msg["content"] == "my transcript"


class TestDebugCode:
    def _mock_resp(self, content: str):
        resp = MagicMock()
        resp.message.content = content
        return resp

    def test_returns_fixed_code_and_explanation(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.return_value = self._mock_resp(
                "Replaced division with safe check.\n\n```python\nx = 0\n```"
            )
            code, explanation = debug_code("x = 1/0", "ZeroDivisionError", "divide")
        assert code == "x = 0"
        assert "Replaced" in explanation

    def test_ollama_unavailable_raises_runtime_error(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.side_effect = ConnectionError("refused")
            with pytest.raises(RuntimeError, match="Ollama unavailable"):
                debug_code("x = 1/0", "ZeroDivisionError", "divide")

    def test_user_message_contains_code_and_error(self):
        with patch("backend.llm._client") as mock_client:
            mock_client.return_value.chat.return_value = self._mock_resp("pass")
            debug_code("broken_code", "SomeError", "my intent")
            call_args = mock_client.return_value.chat.call_args
            messages = call_args.kwargs.get("messages") or call_args.args[1]
            user_msg = next(m for m in messages if m["role"] == "user")
            assert "broken_code" in user_msg["content"]
            assert "SomeError" in user_msg["content"]
            assert "my intent" in user_msg["content"]
