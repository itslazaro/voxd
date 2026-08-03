"""System tray integration for VOXD (QSystemTrayIcon + menu)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app import __version__
from app.core.engine import EngineState

log = logging.getLogger(__name__)

# State → tray icon/tooltip mapping.
STATUS_TEXT = {
    EngineState.IDLE: "🎤 VOXD Ready",
    EngineState.RECORDING: "🔴 Listening",
    EngineState.TRANSCRIBING: "🧠 Transcribing",
    EngineState.TYPING: "⌨️ Writing",
    EngineState.ERROR: "⚠ Error",
}


class VoxdTray(QSystemTrayIcon):
    """Owns the tray icon, state menu, and emits user-intent signals."""

    toggle_requested = Signal()
    settings_requested = Signal()
    logs_requested = Signal()
    quit_requested = Signal()
    model_download_requested = Signal()

    def __init__(self, icon_path: str | Path, parent: QObject | None = None):
        super().__init__(QIcon(str(icon_path)), parent)
        self.setToolTip(STATUS_TEXT[EngineState.IDLE])
        self._menu = QMenu()
        self._build_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        m = self._menu
        m.clear()

        self._status_action = m.addAction(STATUS_TEXT[EngineState.IDLE])
        self._status_action.setEnabled(False)
        m.addSeparator()

        self._start_action = m.addAction("▶ Start recording")
        self._start_action.triggered.connect(self.toggle_requested.emit)
        self._stop_action = m.addAction("⏹ Stop recording")
        self._stop_action.setEnabled(False)
        self._stop_action.triggered.connect(self.toggle_requested.emit)

        m.addSeparator()
        settings = m.addAction("⚙ Settings")
        settings.triggered.connect(self.settings_requested.emit)
        model = m.addAction("⬇ Download model")
        model.triggered.connect(self.model_download_requested.emit)
        logs = m.addAction("📄 View logs")
        logs.triggered.connect(self.logs_requested.emit)

        m.addSeparator()
        about = m.addAction(f"About VOXD {__version__}")
        about.triggered.connect(self._show_about)
        quit_act = m.addAction("✕ Quit")
        quit_act.triggered.connect(self.quit_requested.emit)

    def set_state(self, state: EngineState) -> None:
        """Update status line and menu enablement for the given state."""
        self.setToolTip(STATUS_TEXT.get(state, STATUS_TEXT[EngineState.IDLE]))
        if hasattr(self, "_status_action"):
            self._status_action.setText(STATUS_TEXT.get(state, "VOXD"))
        if hasattr(self, "_start_action"):
            self._start_action.setEnabled(state in (EngineState.IDLE, EngineState.ERROR))
        if hasattr(self, "_stop_action"):
            self._stop_action.setEnabled(state == EngineState.RECORDING)

    def _on_activated(self, reason) -> None:
        # Single left-click toggles; this covers most DEs and GNOME trays.
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,):
            self.toggle_requested.emit()

    def _show_about(self) -> None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.about(
            None,
            "About VOXD",
            f"<b>VOXD {__version__}</b><br/>"
            "Local-first AI voice dictation.<br/>"
            "Audio is transcribed on your machine and typed into any application.",
        )

    def show_message(
        self, title: str, body: str, icon=QSystemTrayIcon.MessageIcon.Information
    ) -> None:
        self.showMessage(title, body, icon, 4000)
