"""
Integration tests for backend/app.py endpoints via FastAPI TestClient.
All external service calls (LLM, executor, ASR) are mocked.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from backend.app import app

client = TestClient(app)


class TestHealth:
    def test_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestGenerate:
    def test_success(self):
        with patch("backend.app._generate_code", return_value="print('hi')"):
            resp = client.post("/generate", json={"transcript": "print hi"})
        assert resp.status_code == 200
        assert resp.json()["code"] == "print('hi')"

    def test_empty_transcript_still_calls_llm(self):
        with patch("backend.app._generate_code", return_value="pass") as mock_gen:
            resp = client.post("/generate", json={"transcript": ""})
        assert resp.status_code == 200
        mock_gen.assert_called_once_with("")

    def test_ollama_unavailable_returns_503(self):
        with patch("backend.app._generate_code",
                   side_effect=RuntimeError("Ollama unavailable")):
            resp = client.post("/generate", json={"transcript": "do something"})
        assert resp.status_code == 503

    def test_missing_transcript_field_returns_422(self):
        resp = client.post("/generate", json={})
        assert resp.status_code == 422

    def test_unexpected_exception_returns_500(self):
        with patch("backend.app._generate_code", side_effect=ValueError("unexpected")):
            resp = client.post("/generate", json={"transcript": "something"})
        assert resp.status_code == 500


class TestExecute:
    _ok = {"stdout": "hello\n", "stderr": "", "exit_code": 0}

    def test_success(self):
        with patch("backend.app._execute", new=AsyncMock(return_value=self._ok)):
            resp = client.post("/execute", json={"code": "print('hello')"})
        assert resp.status_code == 200
        assert resp.json() == self._ok

    def test_nonzero_exit_code_still_returns_200(self):
        error_result = {"stdout": "", "stderr": "NameError", "exit_code": 1}
        with patch("backend.app._execute", new=AsyncMock(return_value=error_result)):
            resp = client.post("/execute", json={"code": "undefined"})
        assert resp.status_code == 200
        assert resp.json()["exit_code"] == 1

    def test_missing_code_field_returns_422(self):
        resp = client.post("/execute", json={})
        assert resp.status_code == 422


class TestDebug:
    _payload = {"code": "x = 1/0", "error": "ZeroDivisionError", "transcript": "divide"}

    def test_success(self):
        with patch("backend.app._debug_code", return_value=("x = 0", "Fixed division")):
            resp = client.post("/debug", json=self._payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "x = 0"
        assert data["explanation"] == "Fixed division"

    def test_ollama_unavailable_returns_503(self):
        with patch("backend.app._debug_code",
                   side_effect=RuntimeError("Ollama unavailable")):
            resp = client.post("/debug", json=self._payload)
        assert resp.status_code == 503

    def test_missing_fields_returns_422(self):
        resp = client.post("/debug", json={"code": "x = 1/0"})
        assert resp.status_code == 422

    def test_unexpected_exception_returns_500(self):
        with patch("backend.app._debug_code", side_effect=ValueError("unexpected")):
            resp = client.post("/debug", json=self._payload)
        assert resp.status_code == 500


class TestTranscribeEndpoint:
    def test_success(self):
        with patch("backend.app._asr_transcribe",
                   new=AsyncMock(return_value="hello world")):
            resp = client.post(
                "/transcribe",
                files={"audio": ("rec.webm", b"fake_audio", "audio/webm")},
            )
        assert resp.status_code == 200
        assert resp.json()["text"] == "hello world"

    def test_asr_http_exception_propagates(self):
        with patch("backend.app._asr_transcribe",
                   new=AsyncMock(side_effect=HTTPException(503, "ASR down"))):
            resp = client.post(
                "/transcribe",
                files={"audio": ("rec.webm", b"fake_audio", "audio/webm")},
            )
        assert resp.status_code == 503

    def test_unexpected_exception_returns_500(self):
        with patch("backend.app._asr_transcribe",
                   new=AsyncMock(side_effect=RuntimeError("unexpected"))):
            resp = client.post(
                "/transcribe",
                files={"audio": ("rec.webm", b"fake_audio", "audio/webm")},
            )
        assert resp.status_code == 500
