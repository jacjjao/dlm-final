"""
LLM module: code generation and auto-debugging via a local Ollama model.

All calls are synchronous (blocking) — use asyncio.to_thread() at the call site.
"""

import os
import re

from ollama import Client, ResponseError

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

_GENERATE_SYSTEM = (
    "You are an expert Python developer assistant. "
    "The user will speak in Mandarin, English, or a mix of both. "
    "Always start your response with exactly one of these two tags on its own line:\n"
    "TYPE:CODE\n"
    "TYPE:CHAT\n\n"
    "Use TYPE:CODE when the user asks you to write, generate, or create code. "
    "After the tag, output ONLY pure Python code — no markdown fences, no explanations.\n\n"
    "Use TYPE:CHAT when the user is asking a question, requesting an explanation, "
    "or having a conversation that does not require writing new code. "
    "After the tag, answer naturally in the same language the user used."
)

_DEBUG_SYSTEM = (
    "You are an expert Python debugger. "
    "You will be given broken Python code and its error traceback. "
    "First, write one short sentence explaining what you fixed (no code in this line). "
    "Then output the complete fixed Python code inside a ```python code fence. "
    "Nothing else."
)


def _client() -> Client:
    return Client(host=OLLAMA_HOST)


def _strip_fences(text: str) -> str:
    """Return code inside the first ```...``` block, or the raw text if none found."""
    m = re.search(r"```(?:python)?\s*\n?(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text.strip()


def _parse_debug(text: str) -> tuple[str, str]:
    """Return (fixed_code, explanation) from a debug response."""
    m = re.search(r"```(?:python)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        code = m.group(1).strip()
        before = text[: m.start()].strip()
        explanation = before.splitlines()[0][:200] if before else "Code fixed."
    else:
        code = text.strip()
        explanation = "Code fixed."
    return code, explanation


def generate_code(transcript: str) -> tuple[str, str]:
    """Return (response_type, content) where response_type is 'code' or 'chat'."""
    try:
        resp = _client().chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": _GENERATE_SYSTEM},
                {"role": "user",   "content": transcript},
            ],
        )
    except Exception as exc:
        raise RuntimeError(
            f"Ollama unavailable ({OLLAMA_HOST}). "
            f"Run: ollama serve  and  ollama pull {OLLAMA_MODEL}. "
            f"Detail: {exc}"
        ) from exc

    raw = resp.message.content.strip()
    if raw.startswith("TYPE:CHAT"):
        content = raw[len("TYPE:CHAT"):].strip()
        return "chat", content
    if raw.startswith("TYPE:CODE"):
        content = raw[len("TYPE:CODE"):].strip()
        return "code", _strip_fences(content)
    return "code", _strip_fences(raw)


def debug_code(code: str, error: str, transcript: str) -> tuple[str, str]:
    user_msg = (
        f"Original user intent: {transcript}\n\n"
        f"Broken code:\n```python\n{code}\n```\n\n"
        f"Error:\n{error}"
    )

    try:
        resp = _client().chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": _DEBUG_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
        )
    except Exception as exc:
        raise RuntimeError(
            f"Ollama unavailable ({OLLAMA_HOST}). Detail: {exc}"
        ) from exc

    return _parse_debug(resp.message.content)
