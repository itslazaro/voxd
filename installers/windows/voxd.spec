# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for VOXD on Windows. Build: pyinstaller installers/windows/voxd.spec"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent.parent  # repo root

datas = [
    (str(ROOT / "app"), "app"),
    (str(ROOT / "assets" / "icons"), "assets/icons"),
    (str(ROOT / "config" / "default.yaml"), "config"),
    (str(ROOT / "scripts" / "setup_whisper.py"), "scripts"),
]

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "pynput",
    "pynput.keyboard",
    "sounddevice",
    "yaml",
]

a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtNetwork", "PySide6.QtWebEngineCore"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VOXD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "assets" / "icons" / "voxd.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VOXD",
)
