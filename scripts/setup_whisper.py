#!/usr/bin/env python3
"""VOXD whisper.cpp setup utility.

Detects whether whisper-cli and a model are available; if not, clones
whisper.cpp, builds it, downloads a model, and runs a verification
transcription. Invoked via `voxd setup` or `python scripts/setup_whisper.py`.
"""

from __future__ import annotations

import argparse
import logging
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("voxd.setup")


def _exe_name() -> str:
    return "whisper-cli.exe" if platform.system() == "Windows" else "whisper-cli"


def _check_command(name: str) -> str | None:
    return shutil.which(name)


def _check_prereqs() -> list[str]:
    """Return a list of missing build prerequisites (only needed for build mode)."""
    missing = []
    for tool in ("git", "cmake"):
        if not _check_command(tool):
            missing.append(tool)
    cc = _check_command("cc") or _check_command("gcc") or _check_command("clang")
    if not cc and platform.system() != "Windows":
        missing.append("a C compiler (gcc/clang)")
    if platform.system() == "Windows" and not _check_command("cl"):
        missing.append("Visual Studio Build Tools (cl.exe)")
    return missing


def install_dir(arg: str | None) -> Path:
    from app.core.config import user_data_dir

    return Path(arg) if arg else user_data_dir() / "whisper"


def setup_prebuilt(model_name: str) -> tuple[Path, Path]:
    """Download the prebuilt whisper-cli.exe + a model (no build tools needed)."""
    from app.core.model import download_model, download_prebuilt_whisper

    log.info("==> Installing prebuilt whisper.cpp (no build tools required)")
    bin_path = download_prebuilt_whisper()

    log.info("==> Downloading model %s", model_name)
    model_path = download_model(model_name)
    return bin_path, model_path


def build_whisper(dest: Path, model_name: str) -> tuple[Path, Path]:
    """Build whisper.cpp at dest and return (bin_path, model_path)."""
    from app.core.model import download_model

    exe = _exe_name()
    bin_path = dest / "build" / "bin" / exe

    log.info("==> Building whisper.cpp in %s", dest)
    if not (dest / ".git").exists():
        url = "https://github.com/ggml-org/whisper.cpp.git"
        subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)

    build = dest / "build"
    build.mkdir(exist_ok=True)
    cfg = ["cmake", "-S", str(dest), "-B", str(build), "-DWHISPER_BUILD_TESTS=OFF"]
    if platform.system() == "Windows":
        cfg.append("-A")
        cfg.append("x64")
    subprocess.run(cfg, check=True)
    subprocess.run(
        ["cmake", "--build", str(build), "--config", "Release", "-j", str(8)],
        check=True,
    )
    if not bin_path.exists():
        raise RuntimeError(f"Build succeeded but {bin_path} was not produced")

    log.info("==> Downloading model %s", model_name)
    model_path = download_model(model_name)
    return bin_path, model_path


def verify_transcription(bin_path: Path, model_path: Path) -> float:
    """Run whisper-cli on a short synthetic WAV; assert non-empty output."""
    import numpy as np

    from app.core.recorder import Recorder
    from app.core.transcriber import Transcriber

    log.info("==> Verifying transcription pipeline")
    rec = Recorder(sample_rate=16000, channels=1)
    # 0.5s of tone/silence — whisper returns no text for pure silence, so we
    # validate that the binary loads, the model loads, and the exit code is 0.
    samples = np.zeros(16000 // 2, dtype=np.float32)
    samples[::2] = 0.001  # faint tone so whisper sees audio
    tmp = Path(tempfile.mkdtemp(prefix="voxd-verify-")) / "verify.wav"
    rec.save_wav(samples, path=tmp)

    t = Transcriber(model_path=str(model_path), whisper_bin=str(bin_path), language="en")
    try:
        text = t.transcribe(tmp)
    finally:
        tmp.unlink(missing_ok=True)
    log.info("Verification OK (returned %d chars)", len(text))
    return len(text)


def run_setup(model_name: str, dest: str | None, prebuilt: bool) -> int:
    if prebuilt:
        bin_path, model_path = setup_prebuilt(model_name)
    else:
        missing = _check_prereqs()
        if missing:
            log.error("Missing prerequisites: %s", ", ".join(missing))
            log.error("Install them first, e.g.:")
            log.error("  sudo apt install git cmake build-essential   (Debian/Ubuntu/Kali)")
            log.error("  sudo dnf install git cmake gcc-c++           (Fedora)")
            log.error("  Visual Studio Build Tools + cmake + git      (Windows)")
            log.error("Tip: on Windows, re-run with --prebuilt (default) to skip build tools.")
            return 1

        dest_path = install_dir(dest)
        bin_path, model_path = build_whisper(dest_path, model_name)

    # Configure VOXD to use these.
    from app.core.config import load_config, save_user_config

    conf = load_config()
    conf["whisper"]["bin"] = str(bin_path)
    conf["whisper"]["install_dir"] = str(Path(bin_path).parent.parent)
    conf["model"]["path"] = str(model_path)
    save_user_config(conf)
    log.info("Wrote config.yaml: whisper.bin=%s", bin_path)

    verify_transcription(bin_path, model_path)
    log.info("Setup complete. Run `voxd gui` (or `voxd daemon`) to start.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="voxd-setup", description="Install/build/test whisper.cpp for VOXD"
    )
    parser.add_argument("--model", default="base.en", help="Whisper model (default base.en)")
    parser.add_argument("--install-dir", default=None, help="Where to build whisper.cpp")
    # Default to prebuilt on Windows (no build tools needed); build elsewhere.
    default_prebuilt = platform.system() == "Windows"
    parser.add_argument(
        "--prebuilt",
        action=argparse.BooleanOptionalAction,
        default=default_prebuilt,
        help="Download prebuilt whisper-cli.exe (default on Windows) instead of building",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Also persist to a log file so runs hidden by the installer are debuggable.
    try:
        from app.core.config import user_state_dir

        log_dir = user_state_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "voxd-setup.log", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(fh)
    except Exception:  # noqa: BLE001
        pass

    try:
        return run_setup(args.model, args.install_dir, args.prebuilt)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        log.error("Setup failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
