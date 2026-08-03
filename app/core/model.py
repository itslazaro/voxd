"""Whisper model discovery and download helpers."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import urllib.request
from pathlib import Path

from app.core.config import user_data_dir

log = logging.getLogger(__name__)

# Known small models available from whisper.cpp's release mirror.
MODELS = {
    "tiny.en": ("ggml-tiny.en.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin"),
    "tiny": ("ggml-tiny.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"),
    "base.en": ("ggml-base.en.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"),
    "base": ("ggml-base.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"),
    "small.en": ("ggml-small.en.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin"),
    "small": ("ggml-small.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"),
}


def models_dir() -> Path:
    return user_data_dir() / "models"


def find_model() -> str:
    """Return a configured/detected model path, or '' if none found."""
    for path in sorted(models_dir().glob("ggml-*.bin")):
        return str(path)
    # Also pick up models bundled next to the app.
    for path in sorted(_install_models().glob("ggml-*.bin")):
        return str(path)
    return ""


def _install_models() -> Path:
    from app.core.config import project_root

    return project_root() / "models"


def list_models() -> list[str]:
    """Return names of available models (without extension)."""
    found = []
    for path in sorted(models_dir().glob("ggml-*.bin")):
        found.append(path.name.removeprefix("ggml-").removesuffix(".bin"))
    return found


def download_model(name: str, progress: callable | None = None) -> Path:
    """Download a known model into the user data dir. Returns the path."""
    if name not in MODELS:
        raise KeyError(f"Unknown model: {name}. Known: {', '.join(MODELS)}")
    filename, url = MODELS[name]
    dest = models_dir() / filename
    if dest.exists():
        log.info("Model %s already present", filename)
        return dest

    models_dir().mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".bin.part")

    def _report(block_num, block_size, total_size):
        if progress and total_size > 0:
            progress(block_num * block_size, total_size)

    urllib.request.urlretrieve(url, tmp, reporthook=_report)  # noqa: S310 - pinned HTTPS URLs above
    tmp.replace(dest)
    log.info("Downloaded model %s", filename)
    return dest


def download_gguf(name: str) -> Path:
    """Backup path for GGUF-style models (future whisper.cpp support)."""
    return download_model(name)


def ensure_whisper_cpp(install_dir: str | None = None) -> Path:
    """Clone and build whisper.cpp if whisper-cli is missing.

    Returns the path to whisper-cli. Requires git + cmake + a compiler.
    """
    exe = "whisper-cli.exe" if platform.system() == "Windows" else "whisper-cli"
    base = Path(install_dir) if install_dir else user_data_dir() / "whisper.cpp"
    bin_path = base / "build" / "bin" / exe
    if bin_path.exists():
        return bin_path

    base.mkdir(parents=True, exist_ok=True)
    log.info("Cloning whisper.cpp into %s", base)
    if not (base / ".git").exists():
        url = "https://github.com/ggml-org/whisper.cpp.git"
        subprocess.run(["git", "clone", "--depth", "1", url, str(base)], check=True)

    cmake = shutil.which("cmake")
    if not cmake:
        raise RuntimeError("cmake not found; cannot build whisper.cpp")
    build = base / "build"
    build.mkdir(exist_ok=True)
    cfg = ["cmake", "-S", str(base), "-B", str(build), "-DWHISPER_BUILD_TESTS=OFF"]
    subprocess.run(cfg, check=True)
    jobs = str(os.cpu_count() or 2)
    build_cmd = ["cmake", "--build", str(build), "--config", "Release", "-j", jobs]
    subprocess.run(build_cmd, check=True)
    return bin_path
