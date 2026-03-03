from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from livinglink.care.contacts import CaregiverContact


@dataclass(slots=True)
class NotificationMessage:
    severity: str
    reason_code: str
    body: str
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class NotificationResult:
    sent: bool
    reason: str
    channel: str
    timestamp: datetime


class InMemoryConnector:
    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.sent: list[tuple[str, NotificationMessage]] = []

    def send(self, contact: CaregiverContact, message: NotificationMessage) -> str:
        self.sent.append((contact.contact_id, message))
        return f"{self.channel}:{contact.contact_id}:{len(self.sent)}"


class NotificationDispatcher:
    def __init__(
        self,
        connectors: dict[str, InMemoryConnector],
        throttle_seconds: int = 300,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._connectors = connectors
        self._throttle_seconds = throttle_seconds
        self._last_sent: dict[tuple[str, str, str], datetime] = {}
        self._now = now or (lambda: datetime.now(timezone.utc))

    def notify(
        self,
        contact: CaregiverContact,
        message: NotificationMessage,
        channel: str,
        dedupe_key: str,
    ) -> NotificationResult:
        timestamp = self._now()

        if not contact.consented:
            return NotificationResult(False, "CONTACT_NOT_CONSENTED", channel, timestamp)

        if channel not in contact.channels:
            return NotificationResult(False, "CHANNEL_NOT_ALLOWED", channel, timestamp)

        connector = self._connectors.get(channel)
        if connector is None:
            return NotificationResult(False, "CONNECTOR_UNAVAILABLE", channel, timestamp)

        throttle_key = (contact.contact_id, channel, dedupe_key)
        last = self._last_sent.get(throttle_key)
        if last is not None and (timestamp - last).total_seconds() < self._throttle_seconds:
            return NotificationResult(False, "THROTTLED", channel, timestamp)

        connector.send(contact, message)
        self._last_sent[throttle_key] = timestamp
        return NotificationResult(True, "SENT", channel, timestamp)
