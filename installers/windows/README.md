# VOXD — Windows build

Build artifacts:
- `VOXD.exe` — PyInstaller one-folder build (`dist/VOXD/VOXD.exe`)
- `VOXD-setup.exe` — console first-run setup tool (downloads prebuilt Whisper + model)
- `VOXD-<ver>-Setup.exe` — Inno Setup installer (bundles both exes)

## Requirements (build machine)

- Windows 10/11 x64
- Python 3.10+
- Inno Setup 6 (`iscc` on PATH) for the installer

End users need **nothing** beyond the installer: no Python, no git, no cmake,
no Visual Studio Build Tools. The installer runs `VOXD-setup.exe` which
downloads a prebuilt `whisper-cli.exe` + DLLs and a Whisper model.

## Build

```
installers\windows\build-exe.cmd
```

This creates the venv, installs dependencies, runs PyInstaller (for both
`VOXD.exe` and `VOXD-setup.exe`), and — if `iscc` is found — produces the
installer.

## First-run setup (what the installer does)

The Inno installer runs `VOXD-setup.exe --prebuilt` after copying files (a
checkbox lets the user skip). That step:

1. Downloads `whisper-bin-x64.zip` from a pinned whisper.cpp release into
   `%LOCALAPPDATA%\VOXD\whisper\Release\` (contains `whisper-cli.exe` + DLLs).
2. Downloads the `base.en` model into `%LOCALAPPDATA%\VOXD\models\`.
3. Writes `%APPDATA%\VOXD\config.yaml` with the bin + model paths.
4. Runs a verification transcription.

It is idempotent — re-running skips downloads already present. Run it manually
any time with `VOXD-setup.exe` (or `voxd setup`). Setup logs to
`%LOCALAPPDATA%\VOXD\logs\voxd-setup.log`.

To build whisper.cpp from source instead (power users), run
`VOXD-setup.exe --no-prebuilt` (requires git + cmake + Visual Studio Build
Tools).

## Publishing a release (so users can download)

1. Bump the version in `app/__init__.py` (and `pyproject.toml`).
2. Tag and push: `git tag v1.0.1 && git push origin v1.0.1`.
3. CI (`.github/workflows/build-windows.yml`) builds `VOXD.exe`,
   `VOXD-setup.exe`, and `VOXD-<ver>-Setup.exe`; the `Publish Release` workflow
   attaches them to a GitHub Release.

Users download the `*-Setup.exe` from the
[Releases page](https://github.com/itslazaro/voxd/releases). For a build without
tagging, run the *Build Windows* workflow from the Actions tab and grab the
artifacts.

## Antivirus / "not commonly downloaded" warnings

Unsigned exes from a new publisher trigger Chrome's "not commonly downloaded"
warning and Microsoft SmartScreen. Mitigations in place:

- **UPX packing is disabled** in both PyInstaller specs — UPX-packed PyInstaller
  binaries are a major source of AV false positives.
- **Optional code signing**: set repo variable `ENABLE_CODE_SIGNING=true` and
  secrets `WINDOWS_CERT_PFX_BASE64` (base64-encoded pfx) +
  `WINDOWS_CERT_PASSWORD`. CI then signs `VOXD.exe`, `VOXD-setup.exe`, and the
  final `*-Setup.exe` with `signtool` (SHA256, Digicert timestamp). An EV or OV
  certificate + accumulated downloads is what eventually clears SmartScreen.
- **Building reputation**: after a signed release, submit the installer to
  [Microsoft Defender file submission](https://www.microsoft.com/wdsi/filesubmission)
  for analysis, and encourage downloads — SmartScreen reputation grows with
  signed download volume over time.

Until the installer is signed and has reputation, users may see a SmartScreen
"Windows protected your PC" prompt → **More info → Run anyway**, and Chrome's
"dangerous file" → **Keep**. This is expected for any new, unsigned publisher.

## Runtime notes

- Typing uses the native SendInput API (no ydotool/systemd).
- Global hotkey uses `pynput`; the tray menu also exposes Start/Stop.

