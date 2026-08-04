# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the VOXD first-run setup tool (console, onefile).

Builds a small, Qt-free VOXD-setup.exe that downloads the prebuilt whisper-cli
and a Whisper model. Run from the Inno installer post-install, or manually.

Build: pyinstaller installers/windows/voxd-setup.spec
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent.parent  # repo root

datas = [
    (str(ROOT / "config" / "default.yaml"), "config"),
]

hiddenimports = [
    "numpy",
    "sounddevice",
    "yaml",
    "app",
    "app.core.config",
    "app.core.model",
    "app.core.recorder",
    "app.core.transcriber",
]

a = Analysis(
    [str(ROOT / "scripts" / "setup_whisper.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "pynput",
        "pyautogui",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VOXD-setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
