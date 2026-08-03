# Contributing to VOXD

Thanks for contributing! This document covers how to set up a dev environment,
run checks, and submit changes.

## Code of conduct

Be respectful and constructive. This project aims to be friendly to newcomers.

## Getting started

1. Fork and clone the repo.
2. Create a branch: `git checkout -b feature/my-change`
3. Set up the environment:

```bash
python3 -m venv venv
./venv/bin/pip install -e ".[dev]"
```

4. Write tests for your change (`tests/`).
5. Run checks locally:

```bash
./venv/bin/ruff check app/ tests/ scripts/
./venv/bin/pytest tests/ -q
```

## Development commands

```bash
./venv/bin/python -m app.main gui        # tray app
./venv/bin/python -m app.main daemon     # headless daemon
./venv/bin/python -m app.main doctor     # health check
./venv/bin/python -m app.main setup      # install whisper.cpp + model
```

## Project layout

```
app/
├── core/       # recorder, transcriber, typer, cleaner, config, engine, model
├── services/   # daemon, hotkey, tray
├── gui/        # Qt app, settings dialog, logs window
└── main.py     # CLI entrypoint
assets/         # icons, sounds
config/         # default.yaml
installers/     # linux/, windows/ packaging
scripts/        # setup_whisper.py
tests/          # pytest suite
```

## Coding standards

- Python 3.10+, type hints on public APIs.
- Line length ≤ 100. Ruff enforces `E,F,W,I,UP` rules.
- Prefer small modules in `app/core` with no GUI imports.
- Cross-platform code: guard platform-specific imports (ydotool, pynput,
  signal) behind `sys.platform` checks.
- No third-party dependency without a justified reason — the core must stay
  local-first and dependency-light.

## Testing notes

- Tests must not require a microphone, display, or network.
- The `tests/` suite currently covers cleaner, config, recorder, transcriber,
  and the dictation engine (mocked recorder/typer).
- GUI smoke tests run headless via `QT_QPA_PLATFORM=offscreen`.

## Commit conventions

We follow the phase-based commit style established in the project history:

```
Commit N (Phase X): short description

- bullet list of what changed
- why it matters
```

Write meaningful commit messages and keep each commit self-contained.

## Pull request process

1. Run `ruff` and `pytest`; both must pass.
2. Update `CHANGELOG.md` under **Unreleased**.
3. Open the PR against `main` and describe what changed and why.

## Building installers

- Linux deb: `bash installers/linux/build-deb.sh <version>`
- Linux AppImage: `bash installers/linux/build-appimage.sh <version>`
- Windows: `installers\windows\build-exe.cmd`

CI builds these automatically on `v*` tags (see `.github/workflows/`).

## Reporting bugs

Open an issue with:

- Platform and version (`voxd doctor` output helps)
- What you expected vs. what happened
- Any relevant log lines from `~/.local/state/VOXD/logs/voxd.log`
