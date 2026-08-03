# VOXD

**Local-first AI voice dictation.** Hold a hotkey, speak, and VOXD transcribes
your words locally with Whisper and types them into any application — your
browser, terminal, editor, or chat window.

- **Local-first.** Audio is transcribed on your machine. Nothing is uploaded
  unless you explicitly enable a cloud backend.
- **System tray app** with live status: 🎤 Ready · 🔴 Listening · 🧠 Transcribing
  · ⌨️ Writing · ⚠ Error.
- **Cross-platform:** Linux (Wayland) and Windows. macOS planned.
- **Configurable** model, language, hotkey, typing engine, and cleanup rules.

---

## Features

| Feature | Status |
|---|---|
| Whisper.cpp local transcription | ✅ |
| Microphone capture (sounddevice/PortAudio) | ✅ |
| Text cleanup layer | ✅ |
| Wayland typing via ydotool | ✅ |
| Windows typing via SendInput | ✅ |
| System tray app (PySide6/Qt) | ✅ |
| Config file (`config.yaml`) | ✅ |
| First-run Whisper setup (`voxd setup`) | ✅ |
| Linux .deb + AppImage packaging | ✅ |
| Windows .exe + Inno installer | ✅ |
| CI/CD (GitHub Actions) | ✅ |
| macOS | 🔜 Planned |

---

## Installation

### Linux

#### Option A — deb package

```bash
sudo apt install ./VOXD-1.0.0-amd64.deb
```

#### Option B — AppImage

```bash
chmod +x VOXD-1.0.0-x86_64.AppImage
./VOXD-1.0.0-x86_64.AppImage
```

#### Option C — from source

```bash
git clone https://github.com/yourname/voxd.git
cd voxd
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m app.main gui
```

### First-run setup (all installs)

```bash
voxd setup
```

This checks prerequisites (git, cmake, compiler), clones and builds
whisper.cpp, downloads a Whisper model, writes your `config.yaml`, and runs a
verification transcription.

> The model and whisper-cli are stored under
> `~/.local/share/VOXD/` on Linux. No audio leaves your machine.

### Windows

1. Run `VOXD-1.0.0-Setup.exe` (Inno Setup) or unzip the PyInstaller build.
2. Open a terminal in the install dir and run:
   ```powershell
   .\VOXD.exe setup
   ```
3. Launch `VOXD.exe`. Use the tray menu or the global hotkey to dictate.

> Building on Windows requires Visual Studio Build Tools (for whisper.cpp).
> See `installers/windows/README.md`.

---

## Supported platforms

| Platform | Version | Notes |
|---|---|---|
| Linux | GNOME on Wayland (Kali, Debian, Ubuntu, Fedora) | ydotool for typing |
| Windows | 10 / 11 x64 | Native SendInput typing |
| macOS | — | Planned (Phase 2) |

---

## Requirements

### Runtime

- Python 3.10+ (bundled in installers)
- PortAudio-compatible audio (PipeWire/PulseAudio on Linux, WASAPI on Windows)
- Linux: `ydotool` + `ydotoold` running; GNOME Shell for the hotkey binding
- Whisper model (installed via `voxd setup`)

### Build (Linux)

```bash
sudo apt install git cmake build-essential portaudio19-dev libportaudio2 ydotool
```

### Build (Windows)

- Python 3.10+, Inno Setup 6, Visual Studio Build Tools
- See `installers/windows/README.md`

---

## Usage

### System tray

The tray icon reflects the current state and offers:

- ▶ Start recording / ⏹ Stop recording
- ⚙ Settings
- ⬇ Download model
- 📄 View logs
- ✕ Quit

### Hotkey

- **Linux/Wayland:** a GNOME custom keybinding runs `voxd --toggle`
  (installed automatically as **Super+V** by `installers/linux/install.sh`).
  Global key-grabbing is not reliable on Wayland, so the OS binding is the
  supported path.
- **Windows:** a global hotkey via `pynput` (default `F8`, configurable).

### Dictation modes

- **Push-to-talk toggle:** press once to start, press again to stop
  (default).
- **Hold-to-talk:** press = start, release = stop (set
  `hotkey.hold_to_talk: true`).

---

## Configuration

Config lives in `~/.config/VOXD/config.yaml` (Linux) or
`%APPDATA%\VOXD\config.yaml` (Windows). It merges over `config/default.yaml`.

```yaml
model:
  path: /home/user/.local/share/VOXD/models/ggml-base.en.bin
  language: en

audio:
  sample_rate: 16000
  device: ""

hotkey:
  key: f8
  hold_to_talk: false

typing:
  engine: auto            # auto | ydotool | sendinput
  ydotool_socket: /run/user/1000/.ydotool_socket

cleanup:
  enabled: true
  capitalize: true
  add_period: true
  collapse_spaces: true

app:
  start_minimized: true
  autostart_daemon: true
  log_level: info
```

Edit via the tray **Settings** dialog or by hand; changes apply on save.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `whisper-cli not found` | Run `voxd setup` |
| `No model installed` | Run `voxd setup` or download via tray |
| Typing does nothing (Linux) | Ensure `ydotoold` runs: `systemctl --user enable --now ydotool` |
| Nothing typed in target app | Focus the app, then dictate |
| GLIBC errors running whisper | Run `voxd doctor`; the app pins `LD_LIBRARY_PATH` |
| Tray icon missing on GNOME | Enable the **AppIndicator and KStatusNotifierItem** extension |
| Diagnose generally | `voxd doctor` |

Logs: `~/.local/state/VOXD/logs/voxd.log` (Linux),
`%LOCALAPPDATA%\VOXD\logs\voxd.log` (Windows).

---

## Development setup

```bash
git clone https://github.com/yourname/voxd.git
cd voxd
python3 -m venv venv
./venv/bin/pip install -e ".[dev]"
./venv/bin/ruff check app/ tests/ scripts/
./venv/bin/pytest tests/
```

Run the app from source:

```bash
./venv/bin/python -m app.main gui      # tray app
./venv/bin/python -m app.main daemon   # headless daemon
./venv/bin/python -m app.main doctor   # health check
```

See `CONTRIBUTING.md` for contribution guidelines and `AUDIT.md` for the
original prototype analysis.

---

## Security & privacy

VOXD is local-first by design:

- Audio is captured, transcribed, and typed locally. **No audio is uploaded.**
- No API keys, accounts, or telemetry are required or included.
- Temp WAV files are created with secure `mkstemp` and removed after use.
- The `voxd setup` flow only downloads Whisper models and builds open-source
  code from pinned HTTPS URLs.

---

## License

[MIT](LICENSE)

VOXD uses [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (MIT) and its
prebuilt GGML models.
