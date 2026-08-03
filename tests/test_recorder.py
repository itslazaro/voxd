"""Tests for the recorder (no microphone required)."""

import numpy as np

from app.core.recorder import Recorder


def test_save_wav_roundtrip(tmp_path):
    rec = Recorder(sample_rate=16000, channels=1)
    samples = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
    out = tmp_path / "x.wav"
    path = rec.save_wav(samples, path=out)
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_wav_secure_temp(tmp_path):
    rec = Recorder()
    samples = np.zeros(160, dtype=np.float32)
    path = rec.save_wav(samples)
    assert path.name.startswith("voxd-")
    assert path.name.endswith(".wav")
    assert path.exists()
    path.unlink()


def test_save_wav_clips_out_of_range():
    rec = Recorder()
    samples = np.array([2.0, -2.0, 0.5], dtype=np.float32)
    out = rec.save_wav(samples)
    # 16-bit max for +1.0 clip
    assert out.stat().st_size > 0
    out.unlink()


def test_stop_with_no_audio_returns_empty():
    rec = Recorder()
    # not started → empty buffer
    data = rec.stop()
    assert data.size == 0
