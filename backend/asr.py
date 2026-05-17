"""
Proxy module: forwards audio to the sherpa-onnx ASR microservice (port 8001).
"""

import os

import httpx
from fastapi import HTTPException, UploadFile

ASR_SERVICE_URL = os.getenv("ASR_SERVICE_URL", "http://localhost:8001")
_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)


async def transcribe(audio: UploadFile) -> str:
    data = await audio.read()
    if not data:
        raise HTTPException(422, detail="Received empty audio file.")

    filename = audio.filename or "recording.webm"
    content_type = audio.content_type or "audio/webm"

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{ASR_SERVICE_URL}/transcribe",
                files={"audio": (filename, data, content_type)},
            )
            resp.raise_for_status()
        except httpx.ConnectError:
            raise HTTPException(
                503,
                detail=(
                    "ASR service is unavailable. "
                    "Start it with: cd asr && docker compose up"
                ),
            )
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                exc.response.status_code,
                detail=f"ASR service error: {exc.response.text}",
            )

    return resp.json()["text"]
