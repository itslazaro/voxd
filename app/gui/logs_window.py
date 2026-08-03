"""Log viewer window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from app.core.config import user_state_dir


class LogsWindow(QDialog):
    """Show the current VOXD log file, refreshing periodically."""

    def __init__(self, log_file: Path | None = None, parent=None):
        super().__init__(parent)
        self._log_file = log_file or (user_state_dir() / "logs" / "voxd.log")
        self.setWindowTitle("VOXD — Logs")
        self.resize(720, 460)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<tt>{self._log_file}</tt>"))

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        layout.addWidget(self.view)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load)
        buttons = QDialogButtonBox()
        buttons.addButton(self.refresh_btn, QDialogButtonBox.ButtonRole.ActionRole)
        close = QDialogButtonBox.StandardButton.Close
        buttons.addButton(close).clicked.connect(self.reject)
        layout.addWidget(buttons)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load)
        self._timer.start(2000)
        self._load()

    def _load(self) -> None:
        if not self._log_file.exists():
            self.view.setPlainText("(no log file yet)")
            return
        try:
            data = self._log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            data = "(log unreadable)"
        cursor = self.view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.view.setPlainText(data)
        if self._timer.isActive():
            cursor.movePosition(cursor.MoveOperation.End)
            self.view.setTextCursor(cursor)
