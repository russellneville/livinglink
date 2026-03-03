from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from livinglink.core.event_bus import EventBus

# Interaction states exposed by the UI (matches REQUIREMENTS.md R1)
STATES = ("Idle", "Listening", "Thinking", "Speaking", "Confirmation Pending", "Emergency Pending")

_QT_AVAILABLE = False

try:
    from PySide6.QtCore import QObject, QThread, Signal as _Signal

    _QT_AVAILABLE = True

    class _EmergencyBridge(QObject):
        """Routes emergency.prepared events from the escalation engine to the UI thread.

        Emergency dispatch requires human confirmation (REQUIREMENTS.md R6).
        This bridge surfaces the emergency.prepared event on the main thread so the
        UI can show a prominent confirmation prompt before anything is sent.
        """

        emergency_needed = _Signal(str, str)  # (request_id, summary)

        def on_event(self, event: object) -> None:
            payload = getattr(event, "payload", {})
            request_id = str(payload.get("request_id", ""))
            summary = str(payload.get("summary", "Emergency situation detected."))
            self.emergency_needed.emit(request_id, summary)

    class _ConfirmationBridge(QObject):
        """Routes executor confirmation events from the worker thread to the UI thread.

        The executor publishes capability.confirmation_required on whatever thread
        the EventBus handler runs on (the PipelineWorker thread). Qt requires UI
        updates to happen on the main thread. This QObject lives on the main thread;
        its signal delivery is automatically marshalled by Qt's AutoConnection.
        """

        confirmation_needed = _Signal(str, str)  # (request_id, display_message)

        def on_event(self, event: object) -> None:
            """EventBus handler — called from worker thread, emits to main thread."""
            payload = getattr(event, "payload", {})
            request_id = str(payload.get("request_id", ""))
            display_message = str(
                payload.get("display_message", "Please confirm this action.")
            )
            self.confirmation_needed.emit(request_id, display_message)

    class _PipelineWorker(QThread):
        """Runs the voice pipeline off the UI thread to keep the window responsive."""

        state_changed = _Signal(str)

        def __init__(self, bus: EventBus, prompt: str) -> None:
            super().__init__()
            self._bus = bus
            self._prompt = prompt

        def run(self) -> None:
            _run_pipeline(self._bus, self._prompt, self.state_changed.emit)

except ImportError:
    pass


def _run_pipeline(
    bus: EventBus,
    prompt: str,
    state_callback: Callable[[str], None],
) -> None:
    """Core pipeline state sequence — separated from Qt for testability.

    Publishes events to the bus and advances through interaction states.
    The executor subscribes to conversation.received and drives the reply;
    this function sequences the UI states around that.
    """
    from livinglink.core.events import Event

    state_callback("Listening")
    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": prompt},
            source="ui",
        )
    )

    state_callback("Thinking")
    # Executor processes conversation.received synchronously (mock providers).
    # With async providers in later phases, Thinking will persist until reply arrives.

    state_callback("Speaking")
    # TTS output placeholder; TTSProvider output will drive this in Phase 3.

    state_callback("Idle")


def launch_ui(bus: EventBus | None = None) -> None:
    """Desktop UI shell with confirmation and emergency state machine.

    States: Idle → Listening → Thinking → Speaking → Idle
                                        ↘ Confirmation Pending → (Yes/No) → Idle
                                        ↘ Emergency Pending    → (Confirm/Cancel) → Idle

    Args:
        bus: Shared EventBus. If None, a fresh runtime is constructed locally.
    """
    if not _QT_AVAILABLE:
        print("PySide6 is not installed. Install optional dependency: pip install .[ui]")
        return

    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    if bus is None:
        from livinglink.app.main import build_runtime

        bus, _, _ = build_runtime()

    app = QApplication.instance() or QApplication([])

    window = QWidget()
    window.setWindowTitle("LivingLink")
    window.resize(420, 280)

    layout = QVBoxLayout()
    status = QLabel("Status: Idle")
    talk = QPushButton("Talk")

    # Confirmation area — hidden until executor requires a HIGH-risk decision.
    confirm_label = QLabel("")
    confirm_row = QHBoxLayout()
    confirm_yes = QPushButton("Yes, confirm")
    confirm_no = QPushButton("No, cancel")
    confirm_row.addWidget(confirm_yes)
    confirm_row.addWidget(confirm_no)

    # Emergency area — shown when escalation engine prepares an emergency notification.
    emergency_label = QLabel("")
    emergency_row = QHBoxLayout()
    emergency_confirm = QPushButton("Send emergency alert")
    emergency_cancel = QPushButton("Cancel")
    emergency_row.addWidget(emergency_confirm)
    emergency_row.addWidget(emergency_cancel)

    layout.addWidget(status)
    layout.addWidget(talk)
    layout.addWidget(confirm_label)
    layout.addLayout(confirm_row)
    layout.addWidget(emergency_label)
    layout.addLayout(emergency_row)
    window.setLayout(layout)
    window.resize(420, 340)

    confirm_label.hide()
    confirm_yes.hide()
    confirm_no.hide()
    emergency_label.hide()
    emergency_confirm.hide()
    emergency_cancel.hide()

    # Mutable state shared across closures.
    _active: list[_PipelineWorker] = []  # type: ignore[name-defined]
    _pending_request_id: list[str | None] = [None]
    _pending_emergency_id: list[str | None] = [None]

    # --- Capability confirmation bridge ----------------------------------------

    bridge = _ConfirmationBridge()  # type: ignore[name-defined]
    bus.subscribe("capability.confirmation_required", bridge.on_event)

    # --- Emergency bridge (REQUIREMENTS.md R6) ---------------------------------

    emg_bridge = _EmergencyBridge()  # type: ignore[name-defined]
    bus.subscribe("emergency.prepared", emg_bridge.on_event)

    def _show_emergency(request_id: str, summary: str) -> None:
        """Called on main thread. Shows emergency confirmation prompt."""
        _pending_emergency_id[0] = request_id
        status.setText("Status: Emergency Pending")
        emergency_label.setText(f"EMERGENCY: {summary}")
        emergency_confirm.show()
        emergency_cancel.show()
        emergency_label.show()
        talk.setEnabled(False)

    def _hide_emergency() -> None:
        emergency_label.hide()
        emergency_confirm.hide()
        emergency_cancel.hide()
        _pending_emergency_id[0] = None

    emg_bridge.emergency_needed.connect(_show_emergency)

    def on_emergency_confirm() -> None:
        from livinglink.core.events import Event

        request_id = _pending_emergency_id[0]
        if not request_id:
            return
        _hide_emergency()
        talk.setEnabled(True)
        status.setText("Status: Idle")
        bus.publish(
            Event(
                name="emergency.confirmed",
                payload={"request_id": request_id},
                source="ui",
            )
        )

    def on_emergency_cancel() -> None:
        from livinglink.core.events import Event

        request_id = _pending_emergency_id[0]
        if not request_id:
            return
        _hide_emergency()
        talk.setEnabled(True)
        status.setText("Status: Idle")
        bus.publish(
            Event(
                name="emergency.denied",
                payload={"request_id": request_id},
                source="ui",
            )
        )

    emergency_confirm.clicked.connect(on_emergency_confirm)
    emergency_cancel.clicked.connect(on_emergency_cancel)

    def _show_confirmation(request_id: str, display_message: str) -> None:
        """Called on main thread via Qt AutoConnection signal."""
        _pending_request_id[0] = request_id
        status.setText("Status: Confirmation Pending")
        confirm_label.setText(display_message)
        confirm_label.show()
        confirm_yes.show()
        confirm_no.show()

    def _hide_confirmation() -> None:
        confirm_label.hide()
        confirm_yes.hide()
        confirm_no.hide()
        _pending_request_id[0] = None

    bridge.confirmation_needed.connect(_show_confirmation)

    def on_confirm_yes() -> None:
        from livinglink.core.events import Event

        request_id = _pending_request_id[0]
        if not request_id:
            return
        _hide_confirmation()
        talk.setEnabled(True)
        status.setText("Status: Idle")
        bus.publish(
            Event(
                name="capability.confirmation_granted",
                payload={"request_id": request_id},
                source="ui",
            )
        )

    def on_confirm_no() -> None:
        from livinglink.core.events import Event

        request_id = _pending_request_id[0]
        if not request_id:
            return
        _hide_confirmation()
        talk.setEnabled(True)
        status.setText("Status: Idle")
        bus.publish(
            Event(
                name="capability.confirmation_denied",
                payload={"request_id": request_id},
                source="ui",
            )
        )

    confirm_yes.clicked.connect(on_confirm_yes)
    confirm_no.clicked.connect(on_confirm_no)

    # --- Talk button / pipeline worker ----------------------------------------

    def on_state_changed(state: str) -> None:
        # If a confirmation is pending, suppress the Idle transition — Talk
        # re-enables only after the user explicitly confirms or denies.
        if state == "Idle" and _pending_request_id[0] is not None:
            status.setText("Status: Confirmation Pending")
            return
        status.setText(f"Status: {state}")
        if state == "Idle":
            talk.setEnabled(True)
            _active.clear()

    def on_talk() -> None:
        talk.setEnabled(False)
        worker = _PipelineWorker(bus=bus, prompt="Hello LivingLink")  # type: ignore[name-defined]
        worker.state_changed.connect(on_state_changed)
        _active.append(worker)
        worker.start()

    talk.clicked.connect(on_talk)
    window.show()
    app.exec()
