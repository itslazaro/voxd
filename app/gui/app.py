"""Main Qt application: tray + engine wiring."""

from __future__ import annotations

import logging
import sys
import threading

from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.config import project_root
from app.core.engine import EngineState
from app.core.model import MODELS, download_model
from app.main import build_engine

log = logging.getLogger(__name__)


class VoxdApplication:
    """Owns the QApplication, tray, engine, and service wiring."""

    def __init__(self, conf: dict, autostart: bool = True):
        from app.services.daemon import Daemon
        from app.services.hotkey import HotkeyService
        from app.services.tray import VoxdTray

        self.conf = conf
        self.qt = QApplication.instance() or QApplication(sys.argv)
        self.qt.setApplicationName("VOXD")

        self.engine = build_engine(conf)
        self.engine._on_state_change = self._on_state_change

        icon_path = self._icon_path()
        self.tray = VoxdTray(icon_path)
        self.daemon = Daemon(self.engine, enable_signals=True)
        self.hotkeys = HotkeyService(
            on_toggle=self.toggle,
            key=conf.get("hotkey", {}).get("key", "f8"),
        )

        self._connect_tray()
        self._autostart = autostart
        self.logs_window = None

    @staticmethod
    def _icon_path() -> str:
        candidates = [
            project_root() / "assets" / "icons" / "voxd.svg",
            project_root() / "assets" / "icons" / "voxd.png",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return ""

    def _connect_tray(self) -> None:
        self.tray.toggle_requested.connect(self.toggle)
        self.tray.settings_requested.connect(self.open_settings)
        self.tray.logs_requested.connect(self.open_logs)
        self.tray.model_download_requested.connect(self.download_model_prompt)
        self.tray.quit_requested.connect(self.quit)

    # -- state ----------------------------------------------------------

    def _on_state_change(self, state: EngineState) -> None:
        self.tray.set_state(state)
        if state == EngineState.ERROR:
            self.tray.show_message(
                "VOXD Error",
                "Dictation failed. See logs for details.",
                QMessageBox.Icon.Warning,
            )

    # -- actions --------------------------------------------------------

    def toggle(self) -> None:
        if self.engine.state == EngineState.RECORDING:
            self.engine.stop_recording()
        elif not self.engine.is_busy():
            self.engine.start_recording()
        else:
            log.info("toggle ignored while %s", self.engine.state)

    def open_settings(self) -> None:
        from app.gui.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self.conf)
        dlg.exec()
        # Rebuild engine with new config.
        self._reload_engine()

    def open_logs(self) -> None:
        from app.gui.logs_window import LogsWindow

        if self.logs_window is None:
            self.logs_window = LogsWindow()
            self.logs_window.finished.connect(lambda: setattr(self, "logs_window", None))
        self.logs_window.show()
        self.logs_window.raise_()
        self.logs_window.activateWindow()

    def download_model_prompt(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getItem(
            self.qt.activeWindow(), "Download model", "Model:", list(MODELS.keys()), 0, False
        )
        if not ok or not name:
            return
        self.tray.show_message("VOXD", f"Downloading {name}…")

        def _work():
            try:
                download_model(name)
                self.tray.show_message("VOXD", f"Model {name} installed.")
            except Exception as exc:  # noqa: BLE001
                log.exception("model download failed")
                self.tray.show_message("VOXD", f"Download failed: {exc}", QMessageBox.Icon.Critical)

        threading.Thread(target=_work, daemon=True).start()

    def _reload_engine(self) -> None:
        from app.core.config import load_config

        try:
            self.conf = load_config()
            self.engine = build_engine(self.conf)
            self.engine._on_state_change = self._on_state_change
            self.hotkeys._key = self.conf.get("hotkey", {}).get("key", "f8")
            log.info("Engine reloaded with new settings")
        except Exception:  # noqa: BLE001
            log.exception("Failed to reload engine")

    # -- lifecycle ------------------------------------------------------

    def start(self) -> None:
        self.daemon.serve_inline()
        self.hotkeys.start()
        self.tray.show()
        if not self._autostart or not self.conf.get("app", {}).get("start_minimized", True):
            # Nothing to show beyond the tray for a tray-first app.
            self.tray.show_message("VOXD", "Ready. Press your hotkey to dictate.")

    def run(self) -> int:
        self.start()
        return self.qt.exec()

    def quit(self) -> None:
        self.engine.shutdown()
        self.hotkeys.stop()
        self.qt.quit()


def run_gui(conf: dict, autostart: bool = True) -> int:
    app = VoxdApplication(conf, autostart=autostart)
    return app.run()
