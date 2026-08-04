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

## Publishing a release (so users can download)

1. Bump the version in `app/__init__.py` (and `pyproject.toml`).
2. Tag and push: `git tag v1.0.1 && git push origin v1.0.1`.
3. CI (`.github/workflows/build-windows.yml`) builds `VOXD.exe` and
   `VOXD-<ver>-Setup.exe`, then attaches them to a GitHub Release.

Users download the `*-Setup.exe` from the
[Releases page](https://github.com/itslazaro/voxd/releases). For a build without
tagging, run the *Build Windows* workflow from the Actions tab and grab the
artifacts.

## Runtime notes

- The first run needs Whisper: run `VOXD.exe setup` (or the bundled
  `setup_whisper.py`) to build `whisper-cli.exe` and download a model.
- On Windows, typing uses the native SendInput API (no ydotool/systemd).
- Global hotkey uses `pynput`; the tray menu also exposes Start/Stop.
