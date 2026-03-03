from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from livinglink.care.contacts import CaregiverContact, ContactBook
from livinglink.care.escalation import EscalationEngine
from livinglink.care.notifications import InMemoryConnector, NotificationDispatcher
from livinglink.core.event_bus import EventBus
from livinglink.core.events import Event


@dataclass
class ClockStub:
    now: datetime

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def _base_runtime() -> tuple[EventBus, ContactBook, NotificationDispatcher, ClockStub]:
    clock = ClockStub(datetime(2026, 1, 1, tzinfo=timezone.utc))
    bus = EventBus()
    contacts = ContactBook()
    contacts.add(
        CaregiverContact(
            contact_id="cg-1",
            name="Primary Caregiver",
            channels=("email", "webhook"),
            consented=True,
            is_primary=True,
        )
    )
    dispatcher = NotificationDispatcher(
        connectors={
            "email": InMemoryConnector("email"),
            "webhook": InMemoryConnector("webhook"),
        },
        throttle_seconds=300,
        now=lambda: clock.now,
    )
    return bus, contacts, dispatcher, clock


def test_orange_risk_notifies_caregiver_and_logs_decision() -> None:
    bus, contacts, dispatcher, _ = _base_runtime()
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher)
    engine.start()

    decisions: list[Event] = []
    sent: list[Event] = []
    bus.subscribe("escalation.decision", decisions.append)
    bus.subscribe("notification.sent", sent.append)

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "ORANGE", "reason_code": "CONFUSION", "summary": "Repeated confusion"},
            source="test",
        )
    )

    assert len(decisions) == 1
    assert decisions[0].payload["severity"] == "ORANGE"
    assert decisions[0].payload["notify_caregiver"] is True
    assert len(sent) == 1
    assert sent[0].payload["channel"] == "email"


def test_notification_throttling_suppresses_repeat_alerts() -> None:
    bus, contacts, dispatcher, _ = _base_runtime()
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher)
    engine.start()

    suppressed: list[Event] = []
    sent: list[Event] = []
    bus.subscribe("notification.sent", sent.append)
    bus.subscribe("notification.suppressed", suppressed.append)

    event = Event(
        name="risk.signal",
        payload={
            "severity": "ORANGE",
            "reason_code": "CONFUSION",
            "summary": "Repeated confusion",
            "dedupe_key": "confusion-spike",
        },
        source="test",
    )
    bus.publish(event)
    bus.publish(event)

    assert len(sent) == 1
    assert len(suppressed) == 1
    assert suppressed[0].payload["reason"] == "THROTTLED"


def test_red_risk_prepares_emergency_then_dispatches_on_confirmation() -> None:
    bus, contacts, dispatcher, _ = _base_runtime()
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher)
    engine.start()

    prepared: list[Event] = []
    dispatched: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)
    bus.subscribe("emergency.dispatched", dispatched.append)

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "RED", "reason_code": "FALL_RISK", "summary": "Possible fall detected"},
            source="test",
        )
    )

    assert len(prepared) == 1
    request_id = prepared[0].payload["request_id"]
    assert prepared[0].payload["requires_confirmation"] is True
    assert dispatched == []

    bus.publish(
        Event(
            name="emergency.confirmed",
            payload={"request_id": request_id},
            source="ui",
        )
    )

    assert len(dispatched) == 1
    assert dispatched[0].payload["request_id"] == request_id


def test_emergency_can_be_cancelled_by_denial() -> None:
    bus, contacts, dispatcher, _ = _base_runtime()
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher)
    engine.start()

    prepared: list[Event] = []
    cancelled: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)
    bus.subscribe("emergency.cancelled", cancelled.append)

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "RED", "reason_code": "FIRE_ALERT", "summary": "Smoke alarm trigger"},
            source="test",
        )
    )

    request_id = prepared[0].payload["request_id"]
    bus.publish(Event(name="emergency.denied", payload={"request_id": request_id}, source="ui"))

    assert len(cancelled) == 1
    assert cancelled[0].payload["request_id"] == request_id


def test_pending_emergency_expires_after_ttl() -> None:
    bus, contacts, dispatcher, _ = _base_runtime()
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher, pending_ttl_seconds=1)
    engine.start()

    prepared: list[Event] = []
    expired: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)
    bus.subscribe("emergency.expired", expired.append)

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "RED", "reason_code": "UNKNOWN", "summary": "Unknown danger"},
            source="test",
        )
    )

    request_id = prepared[0].payload["request_id"]
    # Force pending emergency to be stale, then trigger any new risk signal.
    engine._pending[request_id].created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

    bus.publish(Event(name="risk.signal", payload={"severity": "GREEN", "reason_code": "NORMAL"}, source="test"))

    assert len(expired) == 1
    assert expired[0].payload["request_id"] == request_id
