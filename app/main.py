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
    cleanup_opts = resolve(conf, "cleanup", {}) or {}

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
    """Toggle dictation from an external trigger (GNOME keybinding, tray)."""
    # The real work happens inside the resident process (daemon or GUI).
    # When launched standalone we signal an existing daemon, or run one-off.
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
    return run_gui(conf, autostart=args.autostart)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="voxd", description="VOXD — local-first AI dictation")
    parser.add_argument("--version", action="version", version=f"VOXD {__version__}")
    parser.add_argument("--log-level", default=os.environ.get("VOXD_LOG_LEVEL", "info"))
    parser.add_argument("--log-dir", default=None)
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("daemon", help="Run the background dictation daemon")
    sub.add_parser("gui", help="Launch the system-tray application (default)")
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
        return cmd_gui(args)
    except ConfigError as exc:
        logging.getLogger(__name__).error("Configuration error: %s", exc)
        return 2
    except Exception:  # noqa: BLE001
        logging.getLogger(__name__).exception("Fatal error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
