from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from livinglink.care.contacts import ContactBook
from livinglink.care.notifications import NotificationDispatcher, NotificationMessage
from livinglink.core.event_bus import EventBus
from livinglink.core.events import Event


@dataclass(slots=True)
class PendingEmergency:
    request_id: str
    created_at: datetime
    summary: str


@dataclass(slots=True)
class EscalationEngine:
    bus: EventBus
    contacts: ContactBook
    notifications: NotificationDispatcher
    auto_ems: bool = False
    pending_ttl_seconds: int = 300
    _pending: dict[str, PendingEmergency] = field(init=False, default_factory=dict)

    def start(self) -> None:
        self.bus.subscribe("risk.signal", self._on_risk_signal)
        self.bus.subscribe("concern.detected", self._on_concern_detected)
        self.bus.subscribe("emergency.confirmed", self._on_emergency_confirmed)
        self.bus.subscribe("emergency.denied", self._on_emergency_denied)

    def _on_concern_detected(self, event: Event) -> None:
        level = str(event.payload.get("level", "GREEN")).upper()
        reason = str(event.payload.get("reason_code", "LLM_CONCERN"))
        context = str(event.payload.get("context", ""))
        request_id = str(event.payload.get("request_id", ""))
        self._on_risk_signal(
            Event(
                name="risk.signal",
                payload={
                    "severity": level,
                    "reason_code": reason,
                    "summary": context or "LLM concern detected",
                    "dedupe_key": f"{request_id}:{reason}",
                },
                source="escalation_engine",
            )
        )

    def _on_risk_signal(self, event: Event) -> None:
        severity = str(event.payload.get("severity", "GREEN")).upper()
        reason = str(event.payload.get("reason_code", "UNSPECIFIED"))
        summary = str(event.payload.get("summary", "No summary provided."))
        dedupe_key = str(event.payload.get("dedupe_key", reason))

        self._expire_pending()
        decision = self._decision_for(severity)
        self._publish_decision(severity, reason, decision)

        if decision["notify_caregiver"]:
            self._notify_caregivers(severity, reason, summary, dedupe_key)

        if decision["prepare_emergency"]:
            request_id = str(uuid4())
            self._pending[request_id] = PendingEmergency(
                request_id=request_id,
                created_at=datetime.now(timezone.utc),
                summary=summary,
            )
            self.bus.publish(
                Event(
                    name="emergency.prepared",
                    payload={
                        "request_id": request_id,
                        "summary": summary,
                        "severity": severity,
                        "requires_confirmation": not self.auto_ems,
                    },
                    source="escalation_engine",
                )
            )

            if self.auto_ems:
                self._dispatch_ems(request_id)

    def _on_emergency_confirmed(self, event: Event) -> None:
        self._expire_pending()
        request_id = str(event.payload.get("request_id", ""))
        if event.source != "ui":
            self.bus.publish(
                Event(
                    name="emergency.error",
                    payload={"request_id": request_id, "reason": "UNTRUSTED_SOURCE"},
                    source="escalation_engine",
                )
            )
            return

        if request_id not in self._pending:
            self.bus.publish(
                Event(
                    name="emergency.error",
                    payload={"request_id": request_id, "reason": "UNKNOWN_REQUEST"},
                    source="escalation_engine",
                )
            )
            return
        self._dispatch_ems(request_id)

    def _on_emergency_denied(self, event: Event) -> None:
        self._expire_pending()
        request_id = str(event.payload.get("request_id", ""))
        if event.source != "ui":
            self.bus.publish(
                Event(
                    name="emergency.error",
                    payload={"request_id": request_id, "reason": "UNTRUSTED_SOURCE"},
                    source="escalation_engine",
                )
            )
            return

        pending = self._pending.pop(request_id, None)
        if pending is None:
            return

        self.bus.publish(
            Event(
                name="emergency.cancelled",
                payload={"request_id": request_id, "summary": pending.summary},
                source="escalation_engine",
            )
        )

    def _dispatch_ems(self, request_id: str) -> None:
        pending = self._pending.pop(request_id, None)
        if pending is None:
            return

        message = NotificationMessage(
            severity="BLACK",
            reason_code="EMERGENCY_DISPATCH",
            body=pending.summary,
            metadata={"request_id": request_id},
        )
        primary = self.contacts.primary()
        if primary is not None:
            self.notifications.notify(primary, message, "webhook", dedupe_key=request_id)

        self.bus.publish(
            Event(
                name="emergency.dispatched",
                payload={"request_id": request_id, "summary": pending.summary},
                source="escalation_engine",
            )
        )

    def _notify_caregivers(self, severity: str, reason: str, summary: str, dedupe_key: str) -> None:
        message = NotificationMessage(severity=severity, reason_code=reason, body=summary)
        for contact in self.contacts.list_consented():
            for channel in contact.channels:
                if channel == "webhook":
                    continue
                result = self.notifications.notify(contact, message, channel, dedupe_key)
                event_name = "notification.sent" if result.sent else "notification.suppressed"
                self.bus.publish(
                    Event(
                        name=event_name,
                        payload={
                            "contact_id": contact.contact_id,
                            "channel": channel,
                            "reason": result.reason,
                            "severity": severity,
                            "reason_code": reason,
                        },
                        source="escalation_engine",
                    )
                )

    def _publish_decision(self, severity: str, reason: str, decision: dict[str, bool]) -> None:
        self.bus.publish(
            Event(
                name="escalation.decision",
                payload={
                    "severity": severity,
                    "reason_code": reason,
                    **decision,
                },
                source="escalation_engine",
            )
        )

    def _decision_for(self, severity: str) -> dict[str, bool]:
        if severity == "ORANGE":
            return {
                "notify_caregiver": True,
                "prepare_emergency": False,
                "require_human_confirmation": False,
            }
        if severity in {"RED", "BLACK"}:
            return {
                "notify_caregiver": True,
                "prepare_emergency": True,
                "require_human_confirmation": not self.auto_ems,
            }
        return {
            "notify_caregiver": False,
            "prepare_emergency": False,
            "require_human_confirmation": False,
        }

    def _expire_pending(self) -> None:
        if not self._pending:
            return

        now = datetime.now(timezone.utc)
        ttl = timedelta(seconds=self.pending_ttl_seconds)
        expired: list[str] = []
        for request_id, pending in self._pending.items():
            if (now - pending.created_at) > ttl:
                expired.append(request_id)

        for request_id in expired:
            pending = self._pending.pop(request_id)
            self.bus.publish(
                Event(
                    name="emergency.expired",
                    payload={"request_id": request_id, "summary": pending.summary},
                    source="escalation_engine",
                )
            )
