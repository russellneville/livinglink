from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from livinglink.care.contacts import CaregiverContact
from livinglink.care.notifications import InMemoryConnector, NotificationDispatcher, NotificationMessage


@dataclass
class ClockStub:
    now: datetime

    def advance(self, seconds: int) -> None:
        self.now = self.now + timedelta(seconds=seconds)


def _base_dispatcher() -> tuple[NotificationDispatcher, InMemoryConnector, ClockStub]:
    clock = ClockStub(datetime(2026, 1, 1, tzinfo=timezone.utc))
    connector = InMemoryConnector("email")
    dispatcher = NotificationDispatcher(
        connectors={"email": connector},
        throttle_seconds=300,
        now=lambda: clock.now,
    )
    return dispatcher, connector, clock


def test_notification_dispatcher_sends_when_allowed() -> None:
    dispatcher, connector, _ = _base_dispatcher()
    contact = CaregiverContact(contact_id="c1", name="A", channels=("email",), consented=True)
    message = NotificationMessage(severity="ORANGE", reason_code="CONFUSION", body="Alert")

    result = dispatcher.notify(contact, message, channel="email", dedupe_key="k1")

    assert result.sent is True
    assert result.reason == "SENT"
    assert len(connector.sent) == 1


def test_notification_dispatcher_throttles_duplicate_within_window() -> None:
    dispatcher, connector, _ = _base_dispatcher()
    contact = CaregiverContact(contact_id="c1", name="A", channels=("email",), consented=True)
    message = NotificationMessage(severity="ORANGE", reason_code="CONFUSION", body="Alert")

    first = dispatcher.notify(contact, message, channel="email", dedupe_key="k1")
    second = dispatcher.notify(contact, message, channel="email", dedupe_key="k1")

    assert first.sent is True
    assert second.sent is False
    assert second.reason == "THROTTLED"
    assert len(connector.sent) == 1


def test_notification_dispatcher_allows_after_throttle_window() -> None:
    dispatcher, connector, clock = _base_dispatcher()
    contact = CaregiverContact(contact_id="c1", name="A", channels=("email",), consented=True)
    message = NotificationMessage(severity="ORANGE", reason_code="CONFUSION", body="Alert")

    dispatcher.notify(contact, message, channel="email", dedupe_key="k1")
    clock.advance(301)
    result = dispatcher.notify(contact, message, channel="email", dedupe_key="k1")

    assert result.sent is True
    assert len(connector.sent) == 2


def test_notification_dispatcher_respects_consent_and_channel() -> None:
    dispatcher, _, _ = _base_dispatcher()
    message = NotificationMessage(severity="ORANGE", reason_code="CONFUSION", body="Alert")

    unconsented = CaregiverContact(contact_id="c1", name="A", channels=("email",), consented=False)
    bad_channel = CaregiverContact(contact_id="c2", name="B", channels=("sms",), consented=True)

    denied_consent = dispatcher.notify(unconsented, message, channel="email", dedupe_key="k1")
    denied_channel = dispatcher.notify(bad_channel, message, channel="email", dedupe_key="k2")

    assert denied_consent.sent is False
    assert denied_consent.reason == "CONTACT_NOT_CONSENTED"
    assert denied_channel.sent is False
    assert denied_channel.reason == "CHANNEL_NOT_ALLOWED"
