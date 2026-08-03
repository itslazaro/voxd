# VOXD — Phase 1 System Audit

Date: 2026-08-03
Auditor: automated system inspection
Prototype backup: `~/voxd-prototype-backup-20260803-164150`

---

## 1. Operating System

| Item | Value |
|---|---|
| Distro | Kali GNU/Linux Rolling 2026.3 |
| Kernel | 7.0.12+kali-amd64 (x86_64) |
| Desktop | GNOME |
| Session | Wayland |
| Architecture | x86_64 |

## 2. Toolchain

| Item | Version |
|---|---|
| Python | 3.13.14 (`/usr/bin/python3`) |
| pip | 26.1.2 |
| Node | v24.18.0 |
| npm | 11.16.0 |
| gcc / g++ | 15.3.0-1 |
| make | 4.4.1 |
| cmake | 4.3.4 |
| git | 2.53.0 |
| glibc | 2.42-16 |

## 3. Packaging Tools

| Tool | Status |
|---|---|
| pipx | `/usr/bin/pipx` |
| uv | `~/.local/bin/uv` |
| PyInstaller | 6.19.0 |
| poetry | NOT installed |
| venv | available |

## 4. Project Inventory — `~/voxd`

| File | Purpose | Notes |
|---|---|---|
| `voxd.py` | Original all-in-one prototype (pynput F8 hold-to-talk) | Old approach, self-contained |
| `recorder.py` | Daemon (systemd), signal-triggered (SIGUSR1 start / SIGUSR2 stop) | **The live implementation** |
| `cleaner.py` | Post-process text cleanup | Capitalizes + appends period |
| `trigger.py` | Test signal harness | Debug only |
| `start-voxd.sh` | Sends SIGUSR1 to recorder | Binds to GNOME F8 |
| `stop-voxd.sh` | Sends SIGUSR2 to recorder | Binds to GNOME F7 |
| `venv/` | Python 3.13 virtualenv | numpy 2.5.1, sounddevice 0.5.5, pynput 1.8.2, evdev 1.9.3, cffi |
| `.pycache/` | Compiled bytecode | Remove |

### Live systemd user service

- File: `~/.config/systemd/user/voxd.service`
- Runs: `venv/bin/python recorder.py`
- Status: **active (running)** since 2026-08-03 01:09, PID 1672386
- Env: `YDOTOOL_SOCKET=/run/user/1000/.ydotool_socket`

### GNOME keybindings (Wayland)

- `F8` → `/home/lazaro/voxd/start-voxd.sh` (VOXD START)
- `F7` → `/home/lazaro/voxd/stop-voxd.sh` (VOXD Stop)

Note: GNOME Shell custom keybindings run **on Wayland** and correctly deliver
signals to the user service. This is the current trigger path.

## 5. External Components

### Whisper.cpp

- Repo: `~/Downloads/whisper.cpp` (v1.9.1-158-g2ca53bb4, master)
- Binary: `build/bin/whisper-cli`
- Model: `models/ggml-base.en.bin` (142 MB)
- Other models present: test binaries only (`for-tests-*.bin`); `ggml-base.en.bin`
  is the only real model.

**Critical finding — GLIBC shadowing:**

Running `whisper-cli` from an interactive shell fails with:

```
libc.so.6: version `GLIBC_2.38' not found
```

yet the systemd service transcribes successfully (logged at 12:47 today) and the
binary works when `LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu` is exported.

Root cause: the binary's RUNPATH is `build/bin`, and the default dynamic-loader
search resolves `libc.so.6` against a shadowed library rather than the system
`/usr/lib/x86_64-linux-gnu/libc.so.6` (inode 2752542, glibc 2.42, which *does*
provide `GLIBC_2.38`). Explicit `LD_LIBRARY_PATH` overrides this.

**Action required:** VOXD must always launch `whisper-cli` with
`LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu` prepended, or the app must bundle
its own loader configuration. This is environment-fragile and must be handled
inside `Transcriber`.

### ydotool

- Binary: `/usr/local/bin/ydotool`
- Daemon: `ydotoold` running as user (PID 1476609, since Aug 02)
- Socket: `/run/user/1000/.ydotool_socket` (present, mode `srw-------`)
- **No systemd unit for ydotoold** — it was started manually (`pts/0`).
  The prototype depends on this manually-launched daemon. Should be
  packaged as a user service in the final product.

### Audio stack

- PipeWire 1.6.7 with PulseAudio compatibility
- Default source: `alsa_input.pci-0000_00_1f.3.analog-stereo`
- Pulse socket present: `/run/user/1000/pulse/native`
- sounddevice (PortAudio) in venv — works with PipeWire/Pulse compat.

## 6. Current Architecture (as-built)

```
GNOME keybinding (F8/F7, Wayland)
        │
        ▼
start/stop-voxd.sh ──pkill -USR1/-USR2──▶ recorder.py daemon (systemd user unit)
        │                                        │
        │              sd.InputStream (16 kHz, mono, sounddevice)
        │                                        │
        │              temp wav (tempfile.mktemp — insecure)
        │                                        │
        │              whisper-cli -m ggml-base.en.bin -f wav -otxt
        │                                        │
        │              cleaner.clean_text()
        │                                        │
        ▼                                        ▼
   ydotool type  ◀──────────────────  YDOTOOL_SOCKET env
```

Flow is: hold F8 → record; release F8 → stop, transcribe, clean, type.

## 7. Problems Found

### 7.1 Functional / reliability

1. **No error handling.** Any whisper failure, empty audio, or ydotool error
   crashes the dictation flow silently or leaves stray temp files.
2. **Insecure temp files.** `tempfile.mktemp()` is deprecated/unsafe (race).
   Must use `tempfile.NamedTemporaryFile` / `mkstemp`.
3. **Whisper invoked without env fix** — fails under arbitrary shells due to
   GLIBC shadowing (§5). Works today only because systemd env differs.
4. **ydotoold has no systemd unit** — not auto-started; manual daemon.
5. **Socket path drift.** `voxd.py` uses `/tmp/.ydotool_socket` while
   `recorder.py` uses `/run/user/1000/.ydotool_socket`; only the latter exists.
6. **Hardcoded paths.** `/home/lazaro/...`, user UID 1000 baked in.
7. **Two divergent implementations** (`voxd.py` vs `recorder.py`) — drift risk.
8. **pynput in `voxd.py` is X11-oriented**; on Wayland it won't reliably capture
   global keys. Current GNOME-keybinding approach is the correct one for Wayland.
9. **No config file.** Model, hotkey, socket, rate are constants.
10. **No logging.** systemd journal only; no app-level logs, no tray status.
11. **No exit/restart handling.** `Restart=always` only.

### 7.2 Missing dependencies (for Phase 3+)

- PySide6 (not in venv)
- A YAML config loader (PyYAML) or JSON/Toml
- Qt tray on Wayland requires `libayatana-appindicator` / StatusNotifier support
  (GNOME supports AppIndicator extension; fallback to plain QSystemTrayIcon).
- packaging: `build`, `setuptools`, `wheel`
- Windows-only: `pyautogui` (or ctypes SendInput), `pynput`

### 7.3 Security concerns

1. Microphone is opened on every dictation — fine, but audio is written to
   `/tmp` as wav then deleted; no encryption (not required for local app but
   should be noted). Ensure temp dir is 0700.
2. `ydotoold` socket mode `srw-------` — user-owned; acceptable.
3. No network usage today — VOXD is local-first. **Must keep it that way**;
   any future cloud cleanup must be opt-in.
4. No secrets/API keys present. Good.
5. `subprocess.run` with `shell=False` (safe), but arguments built from model
   path — validate path to avoid injection if ever user-configurable.
6. Prototype runs as the invoking user (good, not root).

### 7.4 Packaging requirements

- App must ship/bundle `whisper-cli` + model, or detect them at runtime with a
  first-run setup flow.
- Linux: AppImage (primary) + `.deb` (secondary). AppImage must set
  `LD_LIBRARY_PATH` for bundled libs; AppRun wrapper handles this.
- Windows: PyInstaller + Inno Setup; no ydotool/systemd; use
  `pyautogui`/Windows SendInput + `pynput` hotkeys.
- Model (~142 MB) should NOT be committed to git; downloaded/installed at setup
  via `whisper.cpp/models/download-ggml-model.sh` or a setup utility.
- CI: GitHub Actions (Linux AppImage/deb, Windows exe/installer).

## 8. Migration Recommendations

1. **Backup** — done (`~/voxd-prototype-backup-20260803-164150`).
2. **git init** `~/voxd` with `.gitignore` (venv, __pycache__, models).
3. Keep the **working trigger path** (GNOME keybinding → daemon) while adding
   the Qt tray; do not regress Wayland input.
4. Refactor `recorder.py` logic into `app/core/{recorder,transcriber,typer,cleaner,config}.py`;
   keep behavior identical (signals + daemon) behind a new service layer.
5. Add env-guard in `Transcriber`: prepend `LD_LIBRARY_PATH` on Linux.
6. Replace `tempfile.mktemp` with safe tempfile usage + cleanup in `finally`.
7. Replace constants with `config.yaml` (Phase 4).
8. Add structured logging (stdlib `logging`, file + journald).
9. Package ydotoold as a user systemd unit.
10. Then layer GUI (Phase 3), config (4), Linux (5), Windows (6), CI (7), docs (8).

## 9. Proposed Target Architecture

```
app/
├── core/
│   ├── recorder.py      # sounddevice capture → in-memory float buffer
│   ├── transcriber.py   # whisper-cli subprocess (env-safe), model mgmt
│   ├── typer.py         # platform typing: ydotool (Linux) / SendInput (Win)
│   ├── cleaner.py       # text cleanup
│   └── config.py        # load/save config.yaml, defaults
├── services/
│   ├── daemon.py        # systemd/signal handling (SIGUSR1/SIGUSR2)
│   ├── hotkey.py        # platform hotkey registration
│   └── tray.py          # QSystemTrayIcon + menu (Phases 3)
├── gui/                 # Qt windows (settings, logs, model select)
└── main.py              # entrypoint
assets/{icons,sounds}
config/default.yaml
installers/{linux,windows}
tests/
requirements.txt, README.md, LICENSE, pyproject.toml, CHANGELOG.md
```

## 10. Dependency Plan

Runtime (Linux): `sounddevice`, `numpy`, `PySide6`, `PyYAML`
Linux system: `ydotool`, `whisper.cpp` (bundled or detected)
Runtime (Windows): `pynput` (or keyboard), `pyautogui`, `PySide6`, `PyYAML`, `sounddevice`
Packaging: `PyInstaller`, `build`, `setuptools`
Dev/test: `pytest`, `ruff` (lint), `mypy` (optional)

---

*End of AUDIT.md*
