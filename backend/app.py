"""
VocalCode backend — FastAPI application.

Endpoints
---------
GET  /health      liveness probe
POST /transcribe  audio → {"text": "..."}
POST /generate    transcript → {"code": "..."}
POST /execute     code → {"stdout", "stderr", "exit_code"}
POST /debug       code + error → {"code": "...", "explanation": "..."}
"""

import asyncio

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from .asr import transcribe as _asr_transcribe
from .executor import execute as _execute
from .llm import debug_code as _debug_code
from .llm import generate_code as _generate_code
from .schemas import DebugRequest, ExecuteRequest, GenerateRequest

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="VocalCode", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    """Forward audio to the ASR microservice and return the transcript."""
    try:
        text = await _asr_transcribe(audio)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc
    return {"text": text}


@app.post("/generate")
async def generate(req: GenerateRequest):
    """Generate Python code from a natural-language transcript via Ollama."""
    try:
        code = await asyncio.to_thread(_generate_code, req.transcript)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc
    return {"code": code}


@app.post("/execute")
async def execute(req: ExecuteRequest):
    """Run Python code in a sandboxed environment."""
    result = await _execute(req.code)
    return result


@app.post("/debug")
async def debug(req: DebugRequest):
    """Ask Ollama to fix broken code and return the corrected version."""
    try:
        fixed_code, explanation = await asyncio.to_thread(
            _debug_code, req.code, req.error, req.transcript
        )
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, detail=str(exc)) from exc
    return {"code": fixed_code, "explanation": explanation}
