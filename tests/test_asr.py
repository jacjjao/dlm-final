"""
Tests for backend/asr.py — the HTTP proxy to the ASR microservice.
All httpx network calls are mocked.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from backend.asr import transcribe


def _make_upload(data: bytes = b"fake_audio", filename: str = "rec.webm",
                 content_type: str = "audio/webm"):
    upload = MagicMock()
    upload.read = AsyncMock(return_value=data)
    upload.filename = filename
    upload.content_type = content_type
    return upload


def _mock_async_client(post_return=None, post_side_effect=None):
    """Return a patch context manager for httpx.AsyncClient."""
    mock_instance = AsyncMock()
    if post_side_effect:
        mock_instance.post.side_effect = post_side_effect
    else:
        mock_instance.post.return_value = post_return

    mock_cls = MagicMock()
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    return patch("backend.asr.httpx.AsyncClient", mock_cls), mock_instance


class TestTranscribe:
    async def test_success_returns_text(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"text": "hello world"}
        mock_resp.raise_for_status = MagicMock()

        ctx, _ = _mock_async_client(post_return=mock_resp)
        with ctx:
            result = await transcribe(_make_upload())
        assert result == "hello world"

    async def test_empty_audio_raises_422(self):
        with pytest.raises(HTTPException) as exc_info:
            await transcribe(_make_upload(data=b""))
        assert exc_info.value.status_code == 422

    async def test_asr_service_down_raises_503(self):
        ctx, _ = _mock_async_client(
            post_side_effect=httpx.ConnectError("connection refused")
        )
        with ctx, pytest.raises(HTTPException) as exc_info:
            await transcribe(_make_upload())
        assert exc_info.value.status_code == 503

    async def test_asr_http_error_propagates_status(self):
        error_resp = MagicMock()
        error_resp.status_code = 500
        error_resp.text = "internal error"
        http_error = httpx.HTTPStatusError("error", request=MagicMock(), response=error_resp)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = http_error

        ctx, _ = _mock_async_client(post_return=mock_resp)
        with ctx, pytest.raises(HTTPException) as exc_info:
            await transcribe(_make_upload())
        assert exc_info.value.status_code == 500

    async def test_filename_defaults_when_none(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"text": "ok"}
        mock_resp.raise_for_status = MagicMock()

        ctx, mock_instance = _mock_async_client(post_return=mock_resp)
        upload = _make_upload()
        upload.filename = None
        upload.content_type = None

        with ctx:
            await transcribe(upload)

        files_arg = mock_instance.post.call_args.kwargs["files"]
        filename = files_arg["audio"][0]
        assert filename == "recording.webm"
