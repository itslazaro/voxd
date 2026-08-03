"""High-level dictation engine tying recorder, transcriber, cleaner, typer."""

from __future__ import annotations

import enum
import logging
import threading
from pathlib import Path

from app.core.cleaner import clean_text
from app.core.recorder import Recorder, RecordingError
from app.core.transcriber import Transcriber, TranscriptionError
from app.core.typer import BaseTyper, TypingError

log = logging.getLogger(__name__)


class EngineState(str, enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    TYPING = "typing"
    ERROR = "error"


class DictationEngine:
    """Orchestrate a single dictation pass: record → transcribe → clean → type.

    Runs the heavy pipeline on a background worker thread so the GUI/daemon
    stays responsive. The caller subscribes to state via on_state_change.
    """

    def __init__(
        self,
        transcriber: Transcriber,
        typer: BaseTyper,
        recorder: Recorder,
        cleanup_options: dict | None = None,
        stop_padding: float = 0.3,
        on_state_change=None,
    ):
        self.transcriber = transcriber
        self.typer = typer
        self.recorder = recorder
        self.cleanup_options = cleanup_options or {}
        self.stop_padding = stop_padding
        self._on_state_change = on_state_change
        self._state = EngineState.IDLE
        self._state_lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._hold_release_event = threading.Event()

    @property
    def state(self) -> EngineState:
        with self._state_lock:
            return self._state

    def _set_state(self, state: EngineState) -> None:
        with self._state_lock:
            changed = state != self._state
            self._state = state
        if changed and self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception:  # noqa: BLE001 - never let a callback crash us
                log.exception("state-change callback failed")

    def is_busy(self) -> bool:
        return self.state in (EngineState.RECORDING, EngineState.TRANSCRIBING)

    # -- public control ---------------------------------------------------

    def start_recording(self) -> None:
        """Start recording immediately (toggle mode)."""
        if self.state == EngineState.RECORDING:
            return
        if self.is_busy():
            log.warning("Engine busy (%s); ignoring start", self.state)
            return
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop_recording(self) -> None:
        """Stop recording and let the pipeline finish (toggle mode)."""
        if self.state == EngineState.RECORDING:
            self._hold_release_event.set()

    # -- hold-to-talk -----------------------------------------------------

    def hold_start(self) -> None:
        self._hold_release_event.clear()
        self.start_recording()

    def hold_release(self) -> None:
        self._hold_release_event.set()

    # -- internals --------------------------------------------------------

    def _run(self) -> None:
        self._set_state(EngineState.RECORDING)
        wav_path: Path | None = None
        try:
            self.recorder.start()
            self._hold_release_event.wait(self._max_record_seconds())
            samples = self.recorder.stop()
            if samples.size == 0:
                log.info("No audio captured; aborting")
                self._set_state(EngineState.IDLE)
                return

            wav_path = self.recorder.save_wav(samples)
            log.debug("Saved %s bytes to %s", samples.nbytes, wav_path)

            self._set_state(EngineState.TRANSCRIBING)
            raw = self.transcriber.transcribe(wav_path)
            text = clean_text(raw, **self._cleanup_kwargs())
            if not text:
                log.info("Empty transcription; skipping typing")
                self._set_state(EngineState.IDLE)
                return

            self._set_state(EngineState.TYPING)
            self.typer.type_text(text)
            log.info("Typed %d chars", len(text))
            self._set_state(EngineState.IDLE)
        except (RecordingError, TranscriptionError, TypingError) as exc:
            log.error("Dictation failed: %s", exc)
            self._set_state(EngineState.ERROR)
        except Exception:  # noqa: BLE001
            log.exception("Unexpected dictation failure")
            self._set_state(EngineState.ERROR)
        finally:
            if wav_path is not None:
                try:
                    wav_path.unlink(missing_ok=True)
                    (Path(str(wav_path) + ".txt")).unlink(missing_ok=True)
                except OSError:
                    log.warning("Could not remove temp files", exc_info=True)

    def _cleanup_kwargs(self) -> dict:
        """Map cleanup config onto clean_text kwargs, ignoring unknown keys.

        ``cleanup.enabled`` toggles the layer entirely.
        """
        opts = dict(self.cleanup_options or {})
        opts.pop("enabled", None)
        return opts

    @staticmethod
    def _max_record_seconds() -> float:
        # Safety cap so a lost "release" never records forever.
        return 60.0

    def shutdown(self) -> None:
        self._hold_release_event.set()
