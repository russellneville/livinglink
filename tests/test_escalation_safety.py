"""Safety-focused tests for the escalation engine.

Covers invariants required by REQUIREMENTS.md R5 (caregiver notifications),
R6 (emergency workflow), and N3 (auditability). Complements the functional
tests in test_care_escalation.py with explicit safety-property assertions.
"""
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


def _runtime(
    auto_ems: bool = False,
    throttle_seconds: int = 300,
) -> tuple[EventBus, EscalationEngine, InMemoryConnector, InMemoryConnector, ClockStub]:
    """Returns (bus, engine, email_connector, webhook_connector, clock).

    email_connector — receives caregiver routine notifications (ORANGE/RED).
    webhook_connector — receives emergency dispatch only (after confirmation).
    """
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
    email_connector = InMemoryConnector("email")
    webhook_connector = InMemoryConnector("webhook")
    dispatcher = NotificationDispatcher(
        connectors={"email": email_connector, "webhook": webhook_connector},
        throttle_seconds=throttle_seconds,
        now=lambda: clock.now,
    )
    engine = EscalationEngine(
        bus=bus,
        contacts=contacts,
        notifications=dispatcher,
        auto_ems=auto_ems,
    )
    engine.start()
    return bus, engine, email_connector, webhook_connector, clock


def _red_signal(bus: EventBus) -> None:
    bus.publish(
        Event(
            name="risk.signal",
            payload={
                "severity": "RED",
                "reason_code": "FALL_RISK",
                "summary": "Possible fall",
                "dedupe_key": "fall-risk",
            },
            source="test",
        )
    )


# ---------------------------------------------------------------------------
# R6: Emergency flow must require human confirmation by default
# ---------------------------------------------------------------------------


def test_auto_ems_defaults_to_false() -> None:
    """EscalationEngine must default auto_ems=False — safe default per R6."""
    bus = EventBus()
    contacts = ContactBook()
    dispatcher = NotificationDispatcher(
        connectors={"email": InMemoryConnector("email")},
        throttle_seconds=300,
    )
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher)
    assert engine.auto_ems is False, "auto_ems must default to False (REQUIREMENTS R6)"


def test_emergency_prepared_requires_confirmation_when_auto_ems_false() -> None:
    """emergency.prepared must set requires_confirmation=True when auto_ems=False."""
    bus, _, _, _, _ = _runtime(auto_ems=False)
    prepared: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)
    _red_signal(bus)
    assert len(prepared) == 1
    assert prepared[0].payload["requires_confirmation"] is True


def test_webhook_not_called_before_emergency_confirmed() -> None:
    """Webhook (emergency dispatch channel) must not fire until emergency.confirmed.

    Note: email IS sent immediately to notify the caregiver (ORANGE/RED caregiver alert).
    Only the webhook emergency dispatch channel must be blocked until confirmed.
    """
    bus, _, _, webhook, _ = _runtime(auto_ems=False)
    _red_signal(bus)
    assert len(webhook.sent) == 0, (
        "Webhook (emergency dispatch) must not fire before emergency.confirmed"
    )


def test_webhook_fires_exactly_once_after_confirmed() -> None:
    """Webhook dispatch occurs exactly once, after emergency.confirmed."""
    bus, _, _, webhook, _ = _runtime(auto_ems=False)
    prepared: list[Event] = []
    dispatched: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)
    bus.subscribe("emergency.dispatched", dispatched.append)

    _red_signal(bus)
    assert len(webhook.sent) == 0  # not yet dispatched

    request_id = prepared[0].payload["request_id"]
    bus.publish(
        Event(name="emergency.confirmed", payload={"request_id": request_id}, source="ui")
    )

    assert len(dispatched) == 1
    assert len(webhook.sent) == 1


def test_caregiver_email_notified_immediately_on_red() -> None:
    """For RED severity, caregiver is notified via email immediately (before confirmation).

    The emergency dispatch (webhook) waits for confirmation, but the routine
    caregiver alert does NOT — they need to know something is happening.
    """
    bus, _, email, _, _ = _runtime(auto_ems=False)
    _red_signal(bus)
    assert len(email.sent) == 1, (
        "Caregiver email must be sent immediately for RED; only webhook dispatch waits"
    )


# ---------------------------------------------------------------------------
# N3: Auditability — escalation.decision must always be published
# ---------------------------------------------------------------------------


def test_every_risk_signal_produces_escalation_decision() -> None:
    """Every risk.signal — including GREEN (no-op) — must produce an audit decision."""
    bus, _, _, _, _ = _runtime()
    decisions: list[Event] = []
    bus.subscribe("escalation.decision", decisions.append)

    for severity in ("GREEN", "ORANGE", "RED", "BLACK"):
        bus.publish(
            Event(
                name="risk.signal",
                payload={"severity": severity, "reason_code": "TEST", "summary": "s"},
                source="test",
            )
        )

    assert len(decisions) == 4, "Every severity level must produce an escalation.decision"
    severities = [d.payload["severity"] for d in decisions]
    assert "GREEN" in severities
    assert "RED" in severities


def test_escalation_decision_contains_reason_code() -> None:
    """escalation.decision payload must include reason_code for explainability (N3)."""
    bus, _, _, _, _ = _runtime()
    decisions: list[Event] = []
    bus.subscribe("escalation.decision", decisions.append)

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "ORANGE", "reason_code": "AGITATION", "summary": "s"},
            source="test",
        )
    )

    assert decisions[0].payload.get("reason_code") == "AGITATION"


# ---------------------------------------------------------------------------
# R5: Notification throttling must prevent spam loops
# ---------------------------------------------------------------------------


def test_throttle_prevents_repeated_caregiver_notifications() -> None:
    """Identical risk signals within the throttle window must not spam caregivers."""
    bus, _, email, _, _ = _runtime(throttle_seconds=300)
    suppressed: list[Event] = []
    bus.subscribe("notification.suppressed", suppressed.append)

    for _ in range(5):
        bus.publish(
            Event(
                name="risk.signal",
                payload={
                    "severity": "ORANGE",
                    "reason_code": "CONFUSION",
                    "summary": "s",
                    "dedupe_key": "same-key",
                },
                source="test",
            )
        )

    assert len(email.sent) == 1, "Only one notification should be sent within throttle window"
    assert len(suppressed) == 4, "Remaining four should be suppressed"


def test_unconsented_contact_not_notified() -> None:
    """Contacts without consent must never receive notifications."""
    bus = EventBus()
    contacts = ContactBook()
    contacts.add(
        CaregiverContact(
            contact_id="cg-no-consent",
            name="Unconsented",
            channels=("email",),
            consented=False,
            is_primary=False,
        )
    )
    connector = InMemoryConnector("email")
    dispatcher = NotificationDispatcher(
        connectors={"email": connector}, throttle_seconds=0
    )
    engine = EscalationEngine(bus=bus, contacts=contacts, notifications=dispatcher)
    engine.start()

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "ORANGE", "reason_code": "CONFUSION", "summary": "s"},
            source="test",
        )
    )

    assert len(connector.sent) == 0, "Unconsented contact must not receive notifications"


# ---------------------------------------------------------------------------
# CONCERN-2: emergency.confirmed/denied source should be from trusted source
# ---------------------------------------------------------------------------


def test_emergency_confirmed_from_ui_dispatches() -> None:
    """emergency.confirmed from source='ui' must trigger dispatch (trusted path)."""
    bus, _, _, webhook, _ = _runtime(auto_ems=False)
    prepared: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)

    _red_signal(bus)
    request_id = prepared[0].payload["request_id"]
    bus.publish(
        Event(name="emergency.confirmed", payload={"request_id": request_id}, source="ui")
    )

    assert len(webhook.sent) == 1


def test_emergency_confirmed_from_untrusted_source_does_not_dispatch() -> None:
    """emergency.confirmed from a non-UI source must NOT trigger dispatch.

    Source allowlist should reject this path and publish emergency.error.
    """
    bus, _, _, webhook, _ = _runtime(auto_ems=False)
    prepared: list[Event] = []
    errors: list[Event] = []
    bus.subscribe("emergency.prepared", prepared.append)
    bus.subscribe("emergency.error", errors.append)

    _red_signal(bus)
    request_id = prepared[0].payload["request_id"]
    bus.publish(
        Event(
            name="emergency.confirmed",
            payload={"request_id": request_id},
            source="system",  # untrusted — should be rejected
        )
    )

    assert len(webhook.sent) == 0, "Untrusted source must not trigger emergency dispatch"
    assert len(errors) == 1
    assert errors[0].payload["reason"] == "UNTRUSTED_SOURCE"
