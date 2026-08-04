"""Microphone capture via sounddevice with a safe, memory-buffered record."""

from __future__ import annotations

import tempfile
import threading
import wave
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
except (ImportError, OSError):  # pragma: no cover - no PortAudio / no sounddevice
    sd = None


class RecordingError(Exception):
    """Raised when audio capture fails."""


class Recorder:
    """Record microphone audio into an in-memory float buffer.

    Thread-safe: start()/stop() may be called from any thread.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1, device: str | None = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self._buffer: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._recording = False
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        with self._lock:
            return self._recording

    def _callback(self, indata, frames, time_info, status) -> None:
        with self._lock:
            if self._recording:
                self._buffer.append(indata.copy())

    def start(self) -> None:
        if sd is None:  # pragma: no cover
            raise RecordingError("sounddevice is not installed")
        with self._lock:
            if self._recording:
                return
            self._buffer = []
            self._recording = True
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device or None,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001 - surface any audio init failure
            with self._lock:
                self._recording = False
            raise RecordingError(f"Failed to open microphone: {exc}") from exc

    def stop(self) -> np.ndarray:
        """Stop recording and return concatenated float samples in [-1, 1]."""
        with self._lock:
            self._recording = False
        stream = self._stream
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            finally:
                self._stream = None
        with self._lock:
            data = self._buffer
        if not data:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(data, axis=0).reshape(-1).astype(np.float32)

    def save_wav(self, samples: np.ndarray, path: Path | None = None) -> Path:
        """Persist float samples as a 16-bit PCM mono WAV file.

        Uses a secure temp file when no path is given. Caller owns cleanup.
        """
        if path is None:
            path = self._temp_wav()
        samples = np.asarray(samples, dtype=np.float32)
        pcm = np.clip(samples, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(np.int16)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())
        return path

    @staticmethod
    def _temp_wav() -> Path:
        fd, name = tempfile.mkstemp(prefix="voxd-", suffix=".wav")
        import os

        os.close(fd)
        return Path(name)
