"""VOXD entry point and CLI."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys
from pathlib import Path

from app import __version__
from app.core.config import (
    ConfigError,
    load_config,
    platform_key,
    user_state_dir,
)


def setup_logging(level: str = "info", log_dir: str | None = None) -> Path | None:
    """Configure logging to stderr and a rotating file in the state dir."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    log_file: Path | None = None
    try:
        base = Path(log_dir) if log_dir else user_state_dir() / "logs"
        base.mkdir(parents=True, exist_ok=True)
        log_file = base / "voxd.log"
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handlers.append(fh)
    except OSError:
        pass

    logging.basicConfig(
        level=numeric,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        handlers=handlers,
    )
    return log_file


def build_engine(conf: dict):
    """Construct the full pipeline (recorder, transcriber, typer) from config."""
    from app.core.config import resolve
    from app.core.engine import DictationEngine
    from app.core.recorder import Recorder
    from app.core.transcriber import Transcriber
    from app.core.typer import create_typer

    sample_rate = int(resolve(conf, "audio", "sample_rate", 16000))
    channels = int(resolve(conf, "audio", "channels", 1))
    device = resolve(conf, "audio", "device", "") or None
    model = resolve(conf, "model", "path", "")
    language = resolve(conf, "model", "language", "en") or None
    threads = int(resolve(conf, "whisper", "threads", 4))
    extra = resolve(conf, "whisper", "extra_args", []) or []
    whisper_bin = resolve(conf, "whisper", "bin", "") or None
    ysocket = resolve(conf, "typing", "ydotool_socket", None) or None
    engine = resolve(conf, "typing", "engine", "auto")
    stop_padding = float(resolve(conf, "audio", "stop_padding", 0.3))
    cleanup_opts = conf.get("cleanup", {}) or {}

    if not model:
        from app.core.model import find_model
        from app.core.transcriber import TranscriptionError

        model = find_model()
        if not model:
            raise TranscriptionError(
                "No Whisper model configured or detected. Run the VOXD setup "
                "to install a model, or set model.path in config.yaml."
            )

    recorder = Recorder(sample_rate=sample_rate, channels=channels, device=device)
    transcriber = Transcriber(
        model_path=model,
        whisper_bin=whisper_bin,
        language=language,
        threads=threads,
        extra_args=extra,
    )
    typer = create_typer(engine, socket_path=ysocket)

    return DictationEngine(
        transcriber=transcriber,
        typer=typer,
        recorder=recorder,
        cleanup_options=cleanup_opts,
        stop_padding=stop_padding,
    )


def cmd_daemon(args) -> int:
    from app.services.daemon import Daemon

    conf = load_config()
    engine = build_engine(conf)
    daemon = Daemon(engine, enable_signals=True)
    daemon.run()
    return 0


def cmd_toggle(args) -> int:
    """Toggle dictation from an external trigger (GNOME keybinding, tray).

    Prefers the pidfile path (signal the running instance directly, no
    systemd required) and falls back to the systemd user service.
    """
    from app.services.pidfile import send_toggle

    if send_toggle(force_start=args.start, force_stop=args.stop):
        return 0
    # Fallback: systemd user service (legacy/installed deployments).
    _signal_running_daemon(args.start and "SIGUSR1" or "SIGUSR2")
    return 0


def _signal_running_daemon(sig_name: str) -> None:
    """Send a signal to the systemd user service named voxd, if present."""
    import subprocess

    try:
        subprocess.run(
            ["systemctl", "--user", "kill", "--signal", sig_name, "voxd.service"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        pass


def cmd_gui(args) -> int:
    from app.gui.app import run_gui

    conf = load_config()
    return run_gui(conf, autostart=not getattr(args, "no_autostart", False))


def cmd_setup(args) -> int:
    import scripts.setup_whisper as setup

    argv = ["--model", args.model]
    if args.install_dir:
        argv += ["--install-dir", args.install_dir]
    return setup.main(argv)


def cmd_doctor(args) -> int:
    """Diagnose the VOXD install (whisper-cli, model, typing engine, audio)."""
    from app.core.config import resolve
    from app.core.model import find_model, list_models
    from app.core.transcriber import TranscriptionError, find_whisper_bin

    logger = logging.getLogger("voxd.doctor")
    ok = True
    conf = load_config()

    configured_bin = resolve(conf, "whisper", "bin", "")
    configured_model = resolve(conf, "model", "path", "")

    binp = configured_bin if configured_bin and Path(configured_bin).is_file() else ""
    if not binp:
        try:
            binp = find_whisper_bin()
        except TranscriptionError as exc:
            logger.warning("✗ whisper-cli: %s", exc)
            ok = False
    if binp:
        logger.info("✓ whisper-cli: %s", binp)

    model = configured_model if configured_model and Path(configured_model).is_file() else ""
    if not model:
        model = find_model()
    if model:
        logger.info("✓ model: %s (%s)", model, list_models())
    else:
        logger.warning("✗ no model installed (run: voxd setup)")
        ok = False

    engine = resolve(conf, "typing", "engine", "auto")
    if platform_key() == "linux":
        import shutil

        y = shutil.which("ydotool")
        sock = resolve(conf, "typing", "ydotool_socket", None)
        if y and (not sock or Path(sock).exists()):
            logger.info("✓ typing: ydotool (%s)", y)
        else:
            logger.warning("✗ typing: ydotool missing or socket not found")
            ok = False
    else:
        logger.info("~ typing engine: %s (set via config)", engine)

    try:
        import sounddevice as sd

        devs = sd.query_devices()
        inputs = sum(1 for d in devs if d["max_input_channels"] > 0)
        logger.info("✓ audio: %d input device(s) available", inputs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("✗ audio: %s", exc)
        ok = False

    logger.info("Health: %s", "OK" if ok else "ISSUES FOUND (run: voxd setup)")
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voxd", description="VOXD — local-first AI dictation")
    parser.add_argument("--version", action="version", version=f"VOXD {__version__}")
    parser.add_argument("--log-level", default=os.environ.get("VOXD_LOG_LEVEL", "info"))
    parser.add_argument("--log-dir", default=None)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("daemon", help="Run the background dictation daemon")
    gui = sub.add_parser("gui", help="Launch the system-tray application (default)")
    gui.add_argument("--no-autostart", action="store_true", help="Do not autostart the daemon")
    sub.add_parser("doctor", help="Check the VOXD install")
    setup = sub.add_parser("setup", help="Install/build/test whisper.cpp + model")
    setup.add_argument("--model", default="base.en", help="Whisper model (default base.en)")
    setup.add_argument("--install-dir", default=None, help="Where to build whisper.cpp")
    toggle = sub.add_parser("toggle", help="Toggle dictation (external trigger)")
    toggle.add_argument("--start", action="store_true", help="Force start")
    toggle.add_argument("--stop", action="store_true", help="Force stop")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.log_level, args.log_dir)
    logging.getLogger(__name__).info("VOXD %s starting (platform=%s)", __version__, platform_key())

    command = args.command or "gui"
    try:
        if command == "daemon":
            return cmd_daemon(args)
        if command == "toggle":
            return cmd_toggle(args)
        if command == "setup":
            return cmd_setup(args)
        if command == "doctor":
            return cmd_doctor(args)
        return cmd_gui(args)
    except ConfigError as exc:
        logging.getLogger(__name__).error("Configuration error: %s", exc)
        return 2
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Fatal error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
