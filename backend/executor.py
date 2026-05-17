"""
Code execution in a sandboxed environment.

Primary path  : Docker container (--network none, memory + PID limits)
Fallback path : local subprocess with timeout only (less secure)
"""

import asyncio
import os
import shutil
import subprocess
import tempfile

SANDBOX_IMAGE   = os.getenv("SANDBOX_IMAGE",   "python:3.12-slim")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "10"))
SANDBOX_MEMORY  = os.getenv("SANDBOX_MEMORY",  "256m")


async def execute(code: str) -> dict:
    return await asyncio.to_thread(_run, code)


# ─── Internal ─────────────────────────────────────────────────────────────────

def _run(code: str) -> dict:
    if shutil.which("docker"):
        return _docker_run(code)
    return _local_run(code)


def _docker_run(code: str) -> dict:
    try:
        proc = subprocess.run(
            [
                "docker", "run", "--rm", "-i",
                "--network", "none",
                f"--memory={SANDBOX_MEMORY}",
                "--cpus=0.5",
                "--pids-limit=64",
                SANDBOX_IMAGE,
                "python3", "-",
            ],
            input=code,
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT + 5,  # extra buffer for container startup
        )
        # Cap output size to avoid flooding the UI
        return {
            "stdout": proc.stdout[:8192],
            "stderr": proc.stderr[:4096],
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return _timeout_result()
    except Exception:
        # Docker present but failed (e.g. image not pulled yet) — try locally
        return _local_run(code)


def _local_run(code: str) -> dict:
    """Fallback: run in the host Python process with only a timeout guard."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(code)
        tmp.flush()
        tmp.close()
        proc = subprocess.run(
            ["python3", tmp.name],
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT,
        )
        return {
            "stdout": proc.stdout[:8192],
            "stderr": proc.stderr[:4096],
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return _timeout_result()
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass


def _timeout_result() -> dict:
    return {
        "stdout": "",
        "stderr": f"TimeoutError: execution exceeded {SANDBOX_TIMEOUT} seconds.",
        "exit_code": 1,
    }
