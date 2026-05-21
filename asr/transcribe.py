"""
sherpa-onnx inference wrapper — FireRed ASR2 (offline, int8 quantised).

Uses OfflineRecognizer instead of the old streaming zipformer so the full
audio clip is decoded in one pass, which gives better accuracy on short
voice commands received as uploaded files.
"""

import os
import wave

import numpy as np
import sherpa_onnx

_MODEL_BASE = (
    "/opt/sherpa-onnx/"
    "sherpa-onnx-fire-red-asr2-zh_en-int8-2026-02-26"
)

MODEL_DIR = os.getenv("MODEL_DIR", _MODEL_BASE)
PROVIDER  = os.getenv("ASR_PROVIDER", "cuda")   # "cuda" | "cpu"
N_THREADS = int(os.getenv("ASR_THREADS", "4"))


class Transcriber:
    def __init__(self) -> None:
        self._rec = sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
            encoder=f"{MODEL_DIR}/encoder.int8.onnx",
            decoder=f"{MODEL_DIR}/decoder.int8.onnx",
            tokens=f"{MODEL_DIR}/tokens.txt",
            num_threads=N_THREADS,
            provider=PROVIDER,
        )

    def transcribe(self, wav_path: str) -> str:
        """Return the recognised text for a 16 kHz mono WAV file."""
        samples = _read_wav(wav_path)
        stream = self._rec.create_stream()
        stream.accept_waveform(16000, samples)
        self._rec.decode_stream(stream)
        result = self._rec.get_result(stream)
        return result.text.strip()


def _read_wav(path: str) -> np.ndarray:
    """Read a 16-bit PCM WAV and return a float32 array normalised to [-1, 1]."""
    with wave.open(path, "rb") as f:
        raw = f.readframes(f.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    return samples / 32768.0
