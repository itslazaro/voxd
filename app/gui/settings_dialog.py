"""Settings dialog bound to the VOXD config."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import save_user_config
from app.core.model import MODELS, list_models
from app.services.autostart import autostart_enabled, disable_autostart, enable_autostart

log = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Edit user config; changes are written to config/config.yaml on save."""

    def __init__(self, conf: dict, parent=None):
        super().__init__(parent)
        self._conf = conf
        self.setWindowTitle("VOXD Settings")
        self.setMinimumWidth(480)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        tabs.addTab(self._model_tab(), "Model")
        tabs.addTab(self._audio_tab(), "Audio")
        tabs.addTab(self._hotkey_tab(), "Hotkey")
        tabs.addTab(self._typing_tab(), "Typing")
        tabs.addTab(self._cleanup_tab(), "Cleanup")
        tabs.addTab(self._app_tab(), "Application")

        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # -- tabs -----------------------------------------------------------

    def _model_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.model_path = QLineEdit(self._conf.get("model", {}).get("path", ""))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_model)
        row = QHBoxLayout()
        row.addWidget(self.model_path)
        row.addWidget(browse)
        form.addRow("Model file", self._wrap(row))

        self.language = QLineEdit(self._conf.get("model", {}).get("language", "en"))
        self.language.setPlaceholderText("en, de, fr… (empty = auto)")
        form.addRow("Language", self.language)

        self.model_download = QComboBox()
        self.model_download.addItem("(choose model to download)", "")
        for key in MODELS:
            self.model_download.addItem(key)
        form.addRow("Download model", self.model_download)

        installed = ", ".join(list_models()) or "none"
        form.addRow("Installed models", QLabel(installed))
        return w

    def _audio_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(8000, 192000)
        self.sample_rate.setValue(int(self._conf.get("audio", {}).get("sample_rate", 16000)))
        form.addRow("Sample rate", self.sample_rate)

        self.device = QLineEdit(self._conf.get("audio", {}).get("device", "") or "")
        self.device.setPlaceholderText("empty = default microphone")
        form.addRow("Microphone", self.device)
        return w

    def _hotkey_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.hotkey = QLineEdit(self._conf.get("hotkey", {}).get("key", "f8"))
        form.addRow("Hotkey", self.hotkey)

        self.hold_to_talk = QCheckBox("Hold to talk (press = start, release = stop)")
        self.hold_to_talk.setChecked(bool(self._conf.get("hotkey", {}).get("hold_to_talk", False)))
        form.addRow("Mode", self.hold_to_talk)

        hint = QLabel(
            "Linux/Wayland: hotkey is handled by a GNOME custom keybinding "
            "wired to `voxd --toggle`. Windows: global hotkey via pynput."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #888;")
        form.addRow("", hint)
        return w

    def _typing_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.engine = QComboBox()
        for label, value in (("Auto", "auto"), ("ydotool", "ydotool"), ("SendInput", "sendinput")):
            self.engine.addItem(label, value)
        idx = self.engine.findData(self._conf.get("typing", {}).get("engine", "auto"))
        self.engine.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow("Typing engine", self.engine)

        self.socket = QLineEdit(self._conf.get("typing", {}).get("ydotool_socket", "") or "")
        form.addRow("ydotool socket", self.socket)

        self.cps = QSpinBox()
        self.cps.setRange(0, 2000)
        self.cps.setValue(int(self._conf.get("typing", {}).get("chars_per_second", 0)))
        self.cps.setSuffix(" chars/s (0 = unlimited)")
        form.addRow("Pacing", self.cps)
        return w

    def _cleanup_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        c = self._conf.get("cleanup", {})
        self.cap = QCheckBox("Capitalize sentences")
        self.cap.setChecked(bool(c.get("capitalize", True)))
        self.period = QCheckBox("Add final period")
        self.period.setChecked(bool(c.get("add_period", True)))
        self.collapse = QCheckBox("Collapse whitespace")
        self.collapse.setChecked(bool(c.get("collapse_spaces", True)))

        box = QVBoxLayout()
        box.addWidget(self.cap)
        box.addWidget(self.period)
        box.addWidget(self.collapse)
        form.addRow("Cleanup", self._wrap(box))
        return w

    def _app_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        a = self._conf.get("app", {})
        self.start_minimized = QCheckBox("Start minimized to tray")
        self.start_minimized.setChecked(bool(a.get("start_minimized", True)))
        self.autostart = QCheckBox("Start daemon on launch")
        self.autostart.setChecked(bool(a.get("autostart_daemon", True)))

        self.login_autostart = QCheckBox("Start VOXD at login")
        self.login_autostart.setChecked(autostart_enabled())
        self.login_autostart.setToolTip(
            "Launch VOXD automatically when you log in (no terminal needed)."
        )

        box = QVBoxLayout()
        box.addWidget(self.start_minimized)
        box.addWidget(self.autostart)
        box.addWidget(self.login_autostart)
        form.addRow("Behaviour", self._wrap(box))

        self.log_level = QComboBox()
        for lvl in ("debug", "info", "warning", "error"):
            self.log_level.addItem(lvl)
        self.log_level.setCurrentText(str(a.get("log_level", "info")))
        form.addRow("Log level", self.log_level)
        return w

    # -- helpers --------------------------------------------------------

    @staticmethod
    def _wrap(layout) -> QWidget:
        holder = QWidget()
        holder.setLayout(layout)
        return holder

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Whisper model", str(Path.home()), "Model (*.bin)"
        )
        if path:
            self.model_path.setText(path)

    def _save(self) -> None:
        conf = self._conf
        conf["model"]["path"] = self.model_path.text().strip()
        conf["model"]["language"] = self.language.text().strip()
        conf["audio"]["sample_rate"] = self.sample_rate.value()
        conf["audio"]["device"] = self.device.text().strip() or ""
        conf["hotkey"]["key"] = self.hotkey.text().strip() or "f8"
        conf["hotkey"]["hold_to_talk"] = self.hold_to_talk.isChecked()
        conf["typing"]["engine"] = self.engine.currentData()
        conf["typing"]["ydotool_socket"] = self.socket.text().strip()
        conf["typing"]["chars_per_second"] = self.cps.value()
        conf["cleanup"]["capitalize"] = self.cap.isChecked()
        conf["cleanup"]["add_period"] = self.period.isChecked()
        conf["cleanup"]["collapse_spaces"] = self.collapse.isChecked()
        conf["app"]["start_minimized"] = self.start_minimized.isChecked()
        conf["app"]["autostart_daemon"] = self.autostart.isChecked()

        if self.login_autostart.isChecked():
            if not enable_autostart():
                log.warning("Could not enable login autostart")
        else:
            disable_autostart()
        conf["app"]["log_level"] = self.log_level.currentText()

        save_user_config(conf)
        self.accept()
