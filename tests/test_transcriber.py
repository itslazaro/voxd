"""Tests for the transcriber (uses a stub whisper-cli)."""

import sys
import textwrap
from pathlib import Path

import pytest

from app.core.transcriber import Transcriber, TranscriptionError, find_whisper_bin


def _write_stub_bin(bin_dir: Path) -> Path:
    """Create a fake whisper-cli that writes a .txt next to the input."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    exe = bin_dir / "whisper-cli"
    exe.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env {sys.executable}
            import sys, pathlib
            args = sys.argv[1:]
            wav = args[args.index('-f')+1]
            out = args[args.index('--output-dir')+1]
            pathlib.Path(out).mkdir(parents=True, exist_ok=True)
            pathlib.Path(wav).with_suffix('.wav.txt').write_text('hello world')
            """
        ),
        encoding="utf-8",
    )
    exe.chmod(0o755)
    return exe


def test_transcribe_success(tmp_path):
    exe = _write_stub_bin(tmp_path / "bin")
    model = tmp_path / "model.bin"
    model.write_bytes(b"x")
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"audio")

    t = Transcriber(model_path=str(model), whisper_bin=str(exe), language="en", threads=2)
    assert t.transcribe(wav) == "hello world"
    assert t._command(str(wav), tmp_path)[:3] == [str(exe), "-m", str(model)]


def test_transcribe_missing_file(tmp_path):
    exe = _write_stub_bin(tmp_path / "bin")
    t = Transcriber(model_path="m", whisper_bin=str(exe))
    with pytest.raises(TranscriptionError):
        t.transcribe(tmp_path / "missing.wav")


def test_transcribe_empty_output(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    exe = bin_dir / "whisper-cli"
    exe.write_text("#!/usr/bin/env true\n", encoding="utf-8")
    exe.chmod(0o755)

    model = tmp_path / "m.bin"
    model.write_bytes(b"x")
    wav = tmp_path / "in.wav"
    wav.write_bytes(b"audio")

    t = Transcriber(model_path=str(model), whisper_bin=str(exe))
    assert t.transcribe(wav) == ""


def test_find_whisper_bin_missing():
    import os

    old = os.environ.get("VOXD_WHISPER_DIR")
    os.environ.pop("VOXD_WHISPER_DIR", None)
    try:
        with pytest.raises(TranscriptionError):
            find_whisper_bin()
    finally:
        if old is not None:
            os.environ["VOXD_WHISPER_DIR"] = old


def test_ld_library_path_in_env():
    from app.core.transcriber import _LINUX_SYSTEM_LIB_DIRS

    assert _LINUX_SYSTEM_LIB_DIRS
