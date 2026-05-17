# VocalCode

A voice-driven Python IDE that lets you write, execute, and debug code entirely hands-free.  
Speak in Mandarin, English, or a mix of both — VocalCode transcribes your speech, generates Python code with a local LLM, runs it in a sandboxed environment, and reads the result back to you.

> **Course project** — Deep Learning Multimedia (DLM), Spring 2026

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Configuration](#configuration)
- [Manual Installation](#manual-installation)
- [Usage](#usage)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Project Structure](#project-structure)

---

## Features

- **Bilingual ASR** — Mandarin–English mixed speech recognition via a local sherpa-onnx model (GPU-accelerated)
- **LLM code generation** — Natural language → syntactically correct Python via a local Ollama model (no API key required)
- **Auto-debugging loop** — On execution error, the system automatically feeds the traceback back to the LLM and retries (up to 3 times)
- **Text-to-Speech feedback** — Execution output is read aloud; fully hands-free operation
- **Sandboxed execution** — Generated code runs inside a Docker container (`--network none`, memory cap, PID limit)
- **Accessible UI** — WCAG 2.1 AA compliant; keyboard-navigable; `aria-live` regions for screen readers

---

## Architecture

```
Browser (Vanilla JS)
  │  audio blob (WebM)       JSON response
  ▼                          ▲
FastAPI backend  (port 8000) ─────────────────────────────────
  ├── POST /transcribe  →  ASR microservice (port 8001)
  │                          └─ sherpa-onnx (local GPU model)
  ├── POST /generate    →  Ollama (localhost:11434, local LLM)
  ├── POST /execute     →  Docker sandbox container
  └── POST /debug       →  Ollama (local LLM, auto-fix)
```

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker | 24+ | Required for all services |
| Docker Compose | v2 (plugin) | Ships with Docker Desktop |
| NVIDIA GPU + driver | — | Required for the ASR service; see CPU fallback below |
| NVIDIA Container Toolkit | — | Needed for GPU pass-through to Docker |
| Ollama | latest | Must run **on the host** (not in Docker); install from [ollama.com](https://ollama.com) |
| Modern browser | Chrome 94+ / Firefox 90+ / Edge 94+ | `MediaRecorder` + `SpeechSynthesis` |

> **No GPU?** Edit `compose.yaml`: remove the `deploy.resources` block under `asr` and change `ASR_PROVIDER=cuda` to `ASR_PROVIDER=cpu`.

---

## Quick Start (Docker Compose)

### 1. Clone the repository

```bash
git clone <repo-url>
cd dlm-final
```

### 2. Start Ollama on the host and pull the model

```bash
# Install from https://ollama.com, then:
ollama pull qwen2.5-coder:7b
ollama serve          # runs on http://localhost:11434
```

### 3. Configure environment variables

```bash
cp .env.example .env
# The defaults work out-of-the-box; edit .env to change the model or timeouts
```

### 4. Build and start all services

```bash
docker compose up --build
```

> **First build takes a while** — the ASR image compiles sherpa-onnx from source and downloads a ~400 MB model. Subsequent starts are fast.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Backend docs | http://localhost:8000/docs |
| ASR service | http://localhost:8001 |

### 5. Wait for the ASR model to load

The ASR container prints `[ASR] Model ready.` once the model is loaded (~60–90 s on first run). Until then, `/transcribe` requests return HTTP 503.

```bash
docker compose logs -f asr
```

### Stopping

```bash
docker compose down
```

---

## Configuration

All tuneable values live in `.env` (copied from `.env.example`).

```env
# Ollama — local LLM inference server (must be running on the host)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b

# ASR microservice
ASR_SERVICE_URL=http://localhost:8001

# Sandbox execution
SANDBOX_IMAGE=python:3.12-slim
SANDBOX_TIMEOUT=10
SANDBOX_MEMORY=256m

MAX_DEBUG_RETRIES=3
```

> When running via Docker Compose, `OLLAMA_HOST` and `ASR_SERVICE_URL` are **overridden** by the compose file to use Docker-internal addresses — you do not need to change them.

**Choosing a model** — any Ollama model works; smaller models are faster:

| Model | Size | Speed |
|-------|------|-------|
| `qwen2.5-coder:1.5b` | ~1 GB | fastest |
| `qwen2.5-coder:7b` | ~4 GB | recommended |
| `codellama:7b` | ~4 GB | alternative |

---

## Manual Installation

Use this if you prefer to run without Docker (e.g., for development with hot-reload).

### 1. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the ASR microservice

```bash
cd asr
docker compose up --build    # runs on port 8001
```

### 3. Start Ollama on the host

```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

### 4. Set up environment variables

```bash
cp .env.example .env         # defaults work; no API keys required
```

### 5. Start the FastAPI backend

```bash
uvicorn backend.app:app --reload --port 8000
```

### 6. Build the frontend

```bash
cd frontend
npm install
npm run build       # compiles ts/ → js/ via tsc
cd ..
```

### 7. Serve the frontend

```bash
cd frontend
python3 -m http.server 3000
```

Open http://localhost:3000.

> **Why a local server?** The frontend uses ES modules (`type="module"`), which browsers block when opened as `file://` due to CORS restrictions.

> **Live editing TypeScript:** Run `npm run watch` inside `frontend/` to recompile on every file save.

---

## Usage

### Basic workflow

1. **Click `Record`** (or press `R`) — the browser asks for microphone permission on first use.
2. **Speak your request** in English, Mandarin, or a mix. For example:
   - *"Write a function that returns the Fibonacci sequence up to N"*
   - *"寫一個 for loop 印出 1 到 10"*
   - *"建立一個 function，計算 list 的 average，然後 print 出來"*
3. **Click `Stop`** (or press `R` again) — VocalCode transcribes your speech, generates code, and runs it automatically.
4. **Listen to the result** — the execution output is read aloud. The code appears in the left panel; stdout/stderr appears in the terminal on the right.
5. **Click `Run`** (or press `Space`) at any time to re-run the code in the editor.

### Auto-debugging

If generated code throws an error, VocalCode automatically:
1. Captures the traceback
2. Sends the original code + error to the local LLM for analysis
3. Replaces the editor content with the fixed code
4. Re-executes — up to **3 attempts**

The debug overlay shows the current attempt. If all retries fail, the error is shown in the terminal and read aloud.

### TTS controls

| Action | How |
|--------|-----|
| Mute / unmute | Click the speaker icon in the title bar, or press `M` |
| Replay last audio | Click the replay button `↺` in the status bar |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `R` | Toggle recording (start / stop) |
| `Space` | Run code (when editor is not empty) |
| `M` | Toggle TTS mute |

Shortcuts are disabled when focus is inside a text input.

---

## API Reference

All endpoints accept and return JSON (except `/transcribe` which takes `multipart/form-data`).  
Base URL: `http://localhost:8000`

### `POST /transcribe`

**Request** — `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `audio` | file | Audio file (WebM, MP3, WAV, M4A) |

**Response**

```json
{ "text": "寫一個 for loop 印出 1 到 10" }
```

---

### `POST /generate`

**Request**

```json
{ "transcript": "寫一個 for loop 印出 1 到 10" }
```

**Response**

```json
{ "code": "for i in range(1, 11):\n    print(i)" }
```

---

### `POST /execute`

**Request**

```json
{ "code": "for i in range(1, 11):\n    print(i)" }
```

**Response**

```json
{
  "stdout": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n",
  "stderr": "",
  "exit_code": 0
}
```

---

### `POST /debug`

**Request**

```json
{
  "code": "print(lst[10])",
  "error": "IndexError: list index out of range",
  "transcript": "print the last element of the list"
}
```

**Response**

```json
{
  "code": "print(lst[-1])",
  "explanation": "Fixed IndexError: used -1 to access the last element instead of index 10."
}
```

---

## Testing

### Frontend — manual UI test (no backend required)

```bash
cd frontend && python3 -m http.server 3000
```

- [ ] Page loads without console errors
- [ ] Record button shows pulse animation when active
- [ ] Keyboard shortcuts (`R`, `Space`, `M`) respond correctly
- [ ] Clicking **Clear** resets editor and disables Run/Copy buttons
- [ ] With no backend running, clicking Record → Stop shows a "Cannot reach backend" toast

### Backend — unit tests (Docker)

All external dependencies (Ollama, ASR service, Docker daemon) are mocked; tests run in an isolated container with no GPU or network required.

```bash
# Build and run the full test suite
docker compose -f compose.test.yaml run --rm test

# Run a single test file
docker compose -f compose.test.yaml run --rm test pytest tests/test_llm.py -v
```

| Test file | Module under test | What is covered |
|-----------|------------------|-----------------|
| `tests/test_llm.py` | `backend/llm.py` | `_strip_fences`, `_parse_debug`, code generation, auto-debug, Ollama error handling |
| `tests/test_executor.py` | `backend/executor.py` | stdout/stderr capture, timeout, Docker↔local dispatch, output size cap |
| `tests/test_asr.py` | `backend/asr.py` | Proxy forwarding, empty-audio 422, ASR-down 503, HTTP error propagation |
| `tests/test_api.py` | `backend/app.py` | All four FastAPI endpoints via `TestClient`, 422/500/503 error responses |

### End-to-end test scenarios

**Simple tasks** (expect first-attempt success)

| Prompt | Expected output |
|--------|----------------|
| "Print numbers 1 to 5" | `1 2 3 4 5` (one per line) |
| "Define a function that adds two numbers and call it with 3 and 4" | `7` |
| "Reverse the string hello world" | `dlrow olleh` |

**Intermediate tasks**

| Prompt | Expected output |
|--------|----------------|
| "Generate a list of squares from 1 to 10 using list comprehension" | `[1, 4, 9, 16, 25, 36, 49, 64, 81, 100]` |
| "Calculate the factorial of 6 using recursion" | `720` |

**Auto-debug scenarios**

```python
# IndexError
lst = [1, 2, 3]
print(lst[5])
```

```python
# NameError
print(undefined_variable)
```

```python
# Timeout (sandbox kills after 10 s)
while True:
    pass
```

### Evaluation metrics

| Metric | Formula | Target | Result |
|--------|---------|--------|--------|
| Word Error Rate (WER) | `(S+D+I) / N × 100%` | < 15% | — |
| Code generation accuracy | correct / total | > 70% | — |
| Auto-debug success rate | fixed / triggered | > 60% | — |
| Task completion time | speech-end → TTS-end | < 15 s | — |

---

## Project Structure

```
dlm-final/
├── compose.yaml            # Root Docker Compose — starts all three services
│
├── frontend/
│   ├── Dockerfile          # Two-stage: node (tsc) → nginx:alpine
│   ├── package.json        # devDependency: typescript ^5.4
│   ├── tsconfig.json       # target ES2020, strict, noImplicitAny
│   ├── index.html
│   ├── style.css
│   ├── ts/                 # TypeScript source (source of truth)
│   │   ├── globals.d.ts    # hljs CDN global declaration
│   │   ├── api.ts          # typed fetch wrappers + response interfaces
│   │   ├── recorder.ts     # MediaRecorder wrapper
│   │   ├── editor.ts       # highlight.js-powered code display
│   │   ├── tts.ts          # SpeechSynthesis wrapper
│   │   └── main.ts         # app entry point & pipeline orchestration
│   └── js/                 # compiled output (gitignored, generated by tsc)
│
├── backend/
│   ├── Dockerfile          # python:3.12-slim + Docker CLI for sandbox
│   ├── app.py              # FastAPI routes
│   ├── asr.py              # httpx proxy → ASR microservice
│   ├── llm.py              # Ollama code generation & debugging
│   ├── executor.py         # Docker sandbox (subprocess fallback)
│   └── schemas.py          # Pydantic request/response models
│
├── asr/
│   ├── Dockerfile          # sherpa-onnx build + model download (CUDA)
│   ├── compose.yaml        # Standalone ASR compose (for development)
│   ├── server.py           # FastAPI wrapper (GET /health, POST /transcribe)
│   └── transcribe.py       # sherpa-onnx OnlineRecognizer wrapper
│
├── sandbox/
│   └── Dockerfile          # Optional: custom sandbox image with numpy/pandas
│
├── tests/
│   ├── Dockerfile          # Isolated test runner image (python:3.12-slim)
│   ├── test_api.py         # FastAPI endpoint tests (TestClient)
│   ├── test_asr.py         # ASR proxy tests
│   ├── test_llm.py         # LLM generation & debug tests
│   └── test_executor.py    # Sandbox execution tests
│
├── compose.test.yaml       # Docker Compose for running the test suite
├── pytest.ini              # asyncio_mode = auto
├── .env.example
├── requirements.txt
├── PLAN.md                 # Full architecture & task checklist
└── README.md
```
