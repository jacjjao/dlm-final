"""
sherpa-onnx inference wrapper.

The Transcriber class is initialised once at server startup and shared across
requests.  Each call to transcribe() creates an independent stream, so
concurrent requests are safe without additional locking.
"""

import os
import wave

import numpy as np
import sherpa_onnx

_MODEL_BASE = (
    "/opt/sherpa-onnx/"
    "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
)

MODEL_DIR = os.getenv("MODEL_DIR", _MODEL_BASE)
PROVIDER  = os.getenv("ASR_PROVIDER", "cuda")   # "cuda" | "cpu" | "coreml"
N_THREADS = int(os.getenv("ASR_THREADS", "4"))

# Silence appended after the utterance to flush the encoder's look-ahead buffer
_TAIL_SECS = 0.5


class Transcriber:
    def __init__(self) -> None:
        self._rec = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens  = f"{MODEL_DIR}/tokens.txt",
            encoder = f"{MODEL_DIR}/encoder-epoch-99-avg-1.onnx",
            decoder = f"{MODEL_DIR}/decoder-epoch-99-avg-1.onnx",
            joiner  = f"{MODEL_DIR}/joiner-epoch-99-avg-1.onnx",
            num_threads     = N_THREADS,
            sample_rate     = 16000,
            feature_dim     = 80,
            decoding_method = "greedy_search",
            provider        = PROVIDER,
        )

    def transcribe(self, wav_path: str) -> str:
        """Return the recognised text for a 16 kHz mono WAV file."""
        samples = _read_wav(wav_path)

        stream = self._rec.create_stream()
        stream.accept_waveform(16000, samples)

        tail = np.zeros(int(_TAIL_SECS * 16000), dtype=np.float32)
        stream.accept_waveform(16000, tail)
        stream.input_finished()

        while self._rec.is_ready(stream):
            self._rec.decode_stream(stream)

        result = self._rec.get_result(stream)
        text = result.text if hasattr(result, "text") else result
        return text.strip()


def _read_wav(path: str) -> np.ndarray:
    """Read a 16-bit PCM WAV and return a float32 array normalised to [-1, 1]."""
    with wave.open(path, "rb") as f:
        raw = f.readframes(f.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    return samples / 32768.0
