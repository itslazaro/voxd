"""Whisper transcription via the whisper.cpp CLI, with env-safe invocation."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import user_data_dir

# On some Linux systems the whisper.cpp binary's RUNPATH causes the dynamic
# loader to resolve a shadowed libc. Pinning LD_LIBRARY_PATH to the system lib
# dir guarantees the correct (newer) glibc is used. Applies on all Linux
# distributions; harmless when unneeded.
_LINUX_SYSTEM_LIB_DIRS = [
    "/usr/lib/x86_64-linux-gnu",
    "/usr/lib64",
    "/usr/lib",
]


class TranscriptionError(Exception):
    """Raised when transcription fails."""


def find_whisper_bin() -> str:
    """Locate whisper-cli via config, PATH, or the default install dir."""
    candidates: list[str] = []
    exe = "whisper-cli" if platform.system() != "Windows" else "whisper-cli.exe"

    install_dir = os.environ.get("VOXD_WHISPER_DIR")
    if install_dir:
        candidates.append(str(Path(install_dir) / "build" / "bin" / exe))
        candidates.append(str(Path(install_dir) / "Release" / exe))

    candidates.append(str(user_data_dir() / "whisper" / "Release" / exe))
    candidates.append(str(user_data_dir() / "whisper.cpp" / "build" / "bin" / exe))

    for cand in candidates:
        if Path(cand).is_file():
            return cand

    found = shutil.which(exe)
    if found:
        return found

    raise TranscriptionError(
        "whisper-cli not found. Run the VOXD setup to build it, or set whisper.bin in config.yaml."
    )


class Transcriber:
    """Run whisper-cli on a WAV file and return cleaned text."""

    def __init__(
        self,
        model_path: str,
        whisper_bin: str | None = None,
        *,
        language: str | None = None,
        threads: int = 4,
        extra_args: list[str] | None = None,
    ):
        self.model_path = model_path
        self.whisper_bin = whisper_bin or find_whisper_bin()
        self.language = language
        self.threads = threads
        self.extra_args = extra_args or []

    def _command(self, wav_path: str, output_prefix: Path) -> list[str]:
        cmd = [
            self.whisper_bin,
            "-m",
            self.model_path,
            "-f",
            wav_path,
            "-otxt",
            "-of",
            str(output_prefix),
        ]
        if self.language:
            cmd += ["-l", self.language]
        if self.threads and self.threads > 0:
            cmd += ["-t", str(self.threads)]
        cmd += self.extra_args
        return cmd

    def _env(self) -> dict:
        env = os.environ.copy()
        if platform.system() == "Linux":
            existing = env.get("LD_LIBRARY_PATH", "")
            merged = ":".join(_LINUX_SYSTEM_LIB_DIRS)
            env["LD_LIBRARY_PATH"] = f"{merged}:{existing}" if existing else merged
        return env

    def transcribe(self, wav_path: str | Path) -> str:
        wav_path = str(wav_path)
        if not Path(wav_path).is_file():
            raise TranscriptionError(f"Audio file not found: {wav_path}")

        # Output prefix in a dedicated temp dir so we never collide with the
        # input WAV and cleanup is simple. whisper-cli appends ".txt".
        out_dir = Path(tempfile.mkdtemp(prefix="voxd-transcribe-"))
        output_prefix = out_dir / "out"
        cmd = self._command(wav_path, output_prefix)
        text = ""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self._env(),
                timeout=600,
            )
            if result.returncode != 0:
                raise TranscriptionError(
                    f"whisper-cli failed ({result.returncode}): {result.stderr.strip()}"
                )
            txt = Path(str(output_prefix) + ".txt")
            if txt.is_file():
                text = txt.read_text(encoding="utf-8").strip()
        finally:
            # whisper may crash or be killed; ensure temp dir is removed.
            shutil.rmtree(out_dir, ignore_errors=True)
        return text


def transcribe_file(
    wav_path: str | Path,
    model_path: str,
    **kwargs,
) -> str:
    """Convenience wrapper: build a Transcriber and run it once."""
    return Transcriber(model_path=model_path, **kwargs).transcribe(wav_path)
