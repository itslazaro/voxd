# VOXD — Windows build

Build artifacts:
- `VOXD.exe` — PyInstaller one-folder build (`build/windows/VOXD/VOXD.exe`)
- `VOXD-<ver>-Setup.exe` — Inno Setup installer

## Requirements (build machine)

- Windows 10/11 x64
- Python 3.10+
- Inno Setup 6 (`iscc` on PATH) for the installer
- Git (for `voxd setup` to clone whisper.cpp) or a prebuilt `whisper-cli.exe`

## Build

```
installers\windows\build-exe.cmd
```

This creates the venv, installs dependencies, runs PyInstaller, and — if `iscc`
is found — produces the installer.

## Runtime notes

- The first run needs Whisper: run `VOXD.exe setup` (or the bundled
  `setup_whisper.py`) to build `whisper-cli.exe` and download a model.
- On Windows, typing uses the native SendInput API (no ydotool/systemd).
- Global hotkey uses `pynput`; the tray menu also exposes Start/Stop.
