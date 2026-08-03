# Changelog

All notable changes to VOXD are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

- macOS support (planned)

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

[Unreleased]: https://github.com/yourname/voxd/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourname/voxd/releases/tag/v1.0.0
