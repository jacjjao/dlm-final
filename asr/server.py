"""
VocalCode ASR microservice — FastAPI wrapper around sherpa-onnx.

Endpoints
---------
GET  /health      liveness + readiness probe
POST /transcribe  upload audio → {"text": "..."}
"""

import asyncio
import os
import subprocess
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from transcribe import Transcriber

# ─── Lifespan: load model once at startup ────────────────────────────────────

_transcriber: Transcriber | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _transcriber
    print("[ASR] Loading sherpa-onnx model…", flush=True)
    # Run in thread pool — model loading is blocking and takes several seconds
    _transcriber = await asyncio.to_thread(Transcriber)
    print("[ASR] Model ready.", flush=True)
    yield
    _transcriber = None


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="VocalCode ASR", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_ready": _transcriber is not None,
        "provider": os.getenv("ASR_PROVIDER", "cuda"),
    }


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """
    Accept any audio format supported by ffmpeg (WebM, MP4, MP3, WAV, OGG…),
    convert it to 16 kHz mono WAV, run sherpa-onnx, and return the transcript.

    Response: {"text": "<recognised text>"}
    """
    if _transcriber is None:
        raise HTTPException(503, detail="Model not loaded yet, please retry.")

    data = await audio.read()
    if not data:
        raise HTTPException(422, detail="Received empty audio file.")

    suffix = Path(audio.filename or "audio.webm").suffix or ".webm"

    # Write the uploaded bytes to a temp file
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src_f:
        src_f.write(data)
        src_path = src_f.name

    wav_path = src_path + ".wav"

    try:
        await asyncio.to_thread(_to_wav, src_path, wav_path)
        text = await asyncio.to_thread(_transcriber.transcribe, wav_path)
        return {"text": text}

    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else ""
        raise HTTPException(422, detail=f"Audio conversion failed: {stderr}")

    except Exception as exc:
        raise HTTPException(500, detail=str(exc))

    finally:
        _unlink(src_path)
        _unlink(wav_path)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_wav(src: str, dst: str) -> None:
    """Convert any audio file to 16 kHz mono WAV using ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", src,
            "-ar", "16000",   # resample to 16 kHz
            "-ac", "1",       # mono
            "-f", "wav",
            dst,
        ],
        check=True,
        capture_output=True,
    )


def _unlink(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
