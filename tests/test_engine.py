"""Tests for the dictation engine orchestration."""

import threading
import time

from app.core.engine import DictationEngine, EngineState


class _FakeRecorder:
    def __init__(self, samples):
        self._samples = samples
        self.called_start = False

    def start(self):
        self.called_start = True

    def stop(self):
        return self._samples

    def save_wav(self, samples, path=None):
        import tempfile
        from pathlib import Path

        fd, name = tempfile.mkstemp(suffix=".wav")
        import os

        os.close(fd)
        p = Path(name)
        p.write_bytes(b"audio")
        return p


class _FakeTranscriber:
    def __init__(self, text="hello world"):
        self.text = text

    def transcribe(self, wav_path):
        return self.text


class _FakeTyper:
    def __init__(self):
        self.typed = []
        self.lock = threading.Lock()

    def type_text(self, text):
        with self.lock:
            self.typed.append(text)


def _make_engine(text="hello world", samples=None):
    import numpy as np

    if samples is None:
        samples = np.zeros(16000, dtype=np.float32)
    typer = _FakeTyper()
    engine = DictationEngine(
        transcriber=_FakeTranscriber(text),
        typer=typer,
        recorder=_FakeRecorder(samples),
        cleanup_options={"capitalize": True, "add_period": True},
        on_state_change=lambda s: None,
    )
    return engine, typer


def _run_to_completion(engine):
    """Drive a toggle-mode engine to idle."""
    engine.start_recording()
    engine.stop_recording()  # release the recording wait
    deadline = time.time() + 3
    while engine.state != EngineState.IDLE and time.time() < deadline:
        time.sleep(0.05)


def test_full_pipeline_types_cleaned_text():
    engine, typer = _make_engine("hello world")
    _run_to_completion(engine)
    assert typer.typed and typer.typed[0] == "Hello world."


def test_state_reaches_idle_after_success():
    engine, _ = _make_engine("ok")
    _run_to_completion(engine)
    assert engine.state == EngineState.IDLE


def test_empty_transcription_does_not_type():
    engine, typer = _make_engine("")
    _run_to_completion(engine)
    assert typer.typed == []


def test_busy_start_ignored():
    engine, _ = _make_engine("x")
    # simulate busy
    engine._state = EngineState.RECORDING
    engine.start_recording()
    assert engine.state == EngineState.RECORDING
