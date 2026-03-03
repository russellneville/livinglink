"""Tests for the UI pipeline state sequence and confirmation event contract.

These tests target livinglink.ui.window._run_pipeline directly, which is
extracted from Qt threading to be fully testable without PySide6.
The confirmation bridge (Qt-dependent) is tested via its EventBus contract only.
"""
from __future__ import annotations

from livinglink.core.event_bus import EventBus
from livinglink.core.events import Event
from livinglink.ui.window import STATES, _run_pipeline


def _make_bus() -> EventBus:
    return EventBus()


def test_run_pipeline_emits_states_in_order() -> None:
    """Pipeline must advance through Listening→Thinking→Speaking→Idle in order."""
    bus = _make_bus()
    emitted: list[str] = []
    _run_pipeline(bus, prompt="test", state_callback=emitted.append)
    assert emitted == ["Listening", "Thinking", "Speaking", "Idle"]


def test_run_pipeline_all_states_are_known() -> None:
    """Every emitted state must be in the declared STATES constant."""
    bus = _make_bus()
    emitted: list[str] = []
    _run_pipeline(bus, prompt="test", state_callback=emitted.append)
    for state in emitted:
        assert state in STATES, f"Unexpected state emitted: {state!r}"


def test_run_pipeline_publishes_conversation_received() -> None:
    """Pipeline must publish conversation.received with the prompt payload."""
    bus = _make_bus()
    captured: list[Event] = []
    bus.subscribe("conversation.received", captured.append)

    _run_pipeline(bus, prompt="Hello LivingLink", state_callback=lambda _: None)

    assert len(captured) == 1
    assert captured[0].name == "conversation.received"
    assert captured[0].payload["prompt"] == "Hello LivingLink"
    assert captured[0].source == "ui"


def test_run_pipeline_does_not_publish_extra_events() -> None:
    """Pipeline must not publish events beyond conversation.received in Phase 1."""
    bus = _make_bus()
    all_events: list[Event] = []

    for event_name in ("conversation.received", "policy.decision"):
        bus.subscribe(event_name, all_events.append)

    _run_pipeline(bus, prompt="test", state_callback=lambda _: None)

    # Only conversation.received expected; executor publishes policy.decision
    # once Codex's executor is wired — assert just one event for now.
    assert len(all_events) == 1
    assert all_events[0].name == "conversation.received"


def test_run_pipeline_ends_in_idle() -> None:
    """The final emitted state must always be Idle so the UI re-enables Talk."""
    bus = _make_bus()
    emitted: list[str] = []
    _run_pipeline(bus, prompt="test", state_callback=emitted.append)
    assert emitted[-1] == "Idle"


# ---------------------------------------------------------------------------
# Confirmation event contract tests (headless — no executor subscribed)
# ---------------------------------------------------------------------------

def test_confirmation_pending_is_a_known_state() -> None:
    """'Confirmation Pending' must be in STATES so the UI label is always valid."""
    assert "Confirmation Pending" in STATES


def test_bus_confirmation_granted_is_publishable() -> None:
    """capability.confirmation_granted can be published and received on the bus."""
    bus = _make_bus()
    received: list[Event] = []
    bus.subscribe("capability.confirmation_granted", received.append)

    bus.publish(
        Event(
            name="capability.confirmation_granted",
            payload={"request_id": "req-abc"},
            source="ui",
        )
    )

    assert len(received) == 1
    assert received[0].payload["request_id"] == "req-abc"
    assert received[0].source == "ui"


def test_bus_confirmation_denied_is_publishable() -> None:
    """capability.confirmation_denied can be published and received on the bus."""
    bus = _make_bus()
    received: list[Event] = []
    bus.subscribe("capability.confirmation_denied", received.append)

    bus.publish(
        Event(
            name="capability.confirmation_denied",
            payload={"request_id": "req-xyz"},
            source="ui",
        )
    )

    assert len(received) == 1
    assert received[0].payload["request_id"] == "req-xyz"
    assert received[0].source == "ui"


def test_confirmation_source_is_ui() -> None:
    """Confirmation events published by the UI must carry source='ui'."""
    bus = _make_bus()
    events: list[Event] = []
    bus.subscribe("capability.confirmation_granted", events.append)
    bus.subscribe("capability.confirmation_denied", events.append)

    for name in ("capability.confirmation_granted", "capability.confirmation_denied"):
        bus.publish(Event(name=name, payload={"request_id": "r1"}, source="ui"))

    for event in events:
        assert event.source == "ui", (
            f"Confirmation event {event.name!r} must originate from 'ui', got {event.source!r}"
        )
