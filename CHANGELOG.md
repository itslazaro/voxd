# Changelog

All notable changes to VOXD are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

- macOS support (planned)

## [1.0.4] — 2026-08-05

### Fixed

- **`voxd setup` failed on the AppImage/deb** with
  `ModuleNotFoundError: No module named 'scripts'` — the `scripts` package
  (containing `setup_whisper.py`) wasn't bundled in the Linux installers.
  Both packagers now copy the `scripts/` package next to `app/`, where
  `PYTHONPATH` already points.

## [1.0.3] — 2026-08-05

### Fixed

- **Launching the AppImage (no subcommand) crashed** with
  `AttributeError: 'Namespace' object has no attribute 'no_autostart'` — the
  `--no-autostart` flag only existed on the `gui` subparser, but the default
  command (no subcommand) routed to `cmd_gui` with a namespace that lacked it.
  `cmd_gui` now uses `getattr(args, "no_autostart", False)`.

## [1.0.2] — 2026-08-05

### Fixed

- **Linux installs crashed at startup** with `Configuration error: Default
  config not found` — the AppImage and `.deb` bundled `default.yaml` at the
  wrong path while the app looked for `config/default.yaml` next to the app
  root. Both packagers now bundle config at the expected path, and
  `default_config_path()` falls back to the AppImage/deb layouts if needed
  (`app/core/config.py`).

## [1.0.1] — 2026-08-04

### Added

- **Automated Windows install** — the installer now downloads a prebuilt
  `whisper-cli.exe` + DLLs and a Whisper model at install time. End users need
  nothing beyond the `Setup.exe`: no Python, git, cmake, or Visual Studio
  Build Tools. Powered by a new bundled `VOXD-setup.exe` (console, Qt-free)
  that runs post-install (`app/core/model.py:download_prebuilt_whisper`,
  `scripts/setup_whisper.py --prebuilt`).
- **Optional code signing** in CI — set repo variable `ENABLE_CODE_SIGNING=true`
  plus cert secrets and CI signs `VOXD.exe`, `VOXD-setup.exe`, and the final
  `*-Setup.exe` (SHA256, Digicert timestamp).
- **Stitch UI/UX design prompt** (`docs/STITCH_UI_PROMPT.md`) covering
  Windows, Linux, and macOS (Liquid Glass), including a 3-step "Get Started"
  onboarding flow.
- Release page now auto-generates a full description with download links and
  install instructions per platform.

### Changed

- **UPX packing disabled** in both PyInstaller specs — the biggest source of
  antivirus false positives for PyInstaller binaries.
- `find_whisper_bin` now also searches the prebuilt install location
  (`%LOCALAPPDATA%\VOXD\whisper\Release\`).
- Windows installer adds a "Download the Whisper engine and model now" task
  (checked by default).

### Fixed

- `voxd setup` crashed when `--install-dir` was unset (passed `None` to
  argparse) — `app/main.py:cmd_setup`.

## [1.0.0] — 2026-08-03

Productized the original Whisper dictation prototype into an installable,
cross-platform desktop application.

### Added

- **Local Whisper transcription** — whisper.cpp `whisper-cli` backend with
  `LD_LIBRARY_PATH` guard against GLIBC shadowing on Linux.
- **Background daemon** — systemd user service; SIGUSR1/SIGUSR2 toggle path
  preserved from the prototype (GNOME keybinding compatible on Wayland).
- **System tray application** (PySide6/Qt) with live status:
  🎤 Ready · 🔴 Listening · 🧠 Transcribing · ⌨️ Writing · ⚠ Error.
  Tray menu: Start/Stop recording, Settings, Download model, View logs, Quit.
- **Linux support** — Wayland typing via ydotool; `.deb` and AppImage
  packaging; systemd user units for VOXD and ydotoold; GNOME keybinding
  installer (Super+V → `voxd --toggle`).
- **Windows support** — native SendInput typing, `pynput` global hotkey,
  PyInstaller `VOXD.exe` and Inno Setup installer.
- **Configuration system** — `config.yaml` (model, language, hotkey, typing
  engine, audio, cleanup, app behaviour) with defaults + user merge.
- **First-run setup** — `voxd setup` clones/builds whisper.cpp, downloads a
  model, writes config, and runs a verification transcription. `voxd doctor`
  diagnoses the install.
- **Text cleanup layer** — capitalize sentences, add final period, collapse
  whitespace.
- **CI/CD** — GitHub Actions: lint+tests, Linux (deb+AppImage), Windows
  (exe+installer) with release automation on version tags.
- **Documentation** — README, CONTRIBUTING, AUDIT (prototype analysis).

### Changed

- Prototype `voxd.py`/`recorder.py` unified into a modular `app/` package
  (`core`, `services`, `gui`).
- Insecure `tempfile.mktemp` replaced with secure `mkstemp` + cleanup.
- Hardcoded paths replaced with platform-aware user config/data/state dirs.

### Fixed

- GLIBC `2.38 not found` failure when invoking whisper-cli from arbitrary
  environments.
- ydotool socket path drift (`/tmp/` vs `/run/user/<uid>/`).

### Security

- Local-first: no audio upload, no telemetry, no API keys.
- Model downloads pinned to HTTPS (ggml-org mirror).

[Unreleased]: https://github.com/itslazaro/voxd/compare/v1.0.4...HEAD
[1.0.4]: https://github.com/itslazaro/voxd/releases/tag/v1.0.4
[1.0.3]: https://github.com/itslazaro/voxd/releases/tag/v1.0.3
[1.0.2]: https://github.com/itslazaro/voxd/releases/tag/v1.0.2
[1.0.1]: https://github.com/itslazaro/voxd/releases/tag/v1.0.1
[1.0.0]: https://github.com/itslazaro/voxd/releases/tag/v1.0.0
