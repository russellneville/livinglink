from __future__ import annotations

from datetime import datetime, timedelta, timezone

from livinglink.app.main import build_runtime, demo_round_trip
from livinglink.core.config import RuntimeConfig
from livinglink.core.events import Event
from livinglink.providers.llm.base import ActionRequest, LLMProvider, LLMResponse


class NetworkLLMProvider(LLMProvider):
    requires_network = True

    def generate(self, prompt: str) -> LLMResponse:
        return LLMResponse(reply_text="network reply", requested_actions=[])


class InvalidArgsLLMProvider(LLMProvider):
    def generate(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            reply_text="processing",
            requested_actions=[ActionRequest(name="get_time", arguments={"unexpected": True})],
        )


def test_demo_round_trip_returns_reply_text() -> None:
    reply = demo_round_trip("Hello LivingLink")
    assert reply == "I heard: Hello LivingLink"


def test_executor_executes_allowlisted_low_risk_capability() -> None:
    bus, _, _ = build_runtime()
    policy_events: list[Event] = []
    capability_events: list[Event] = []
    replies: list[Event] = []

    bus.subscribe("policy.decision", policy_events.append)
    bus.subscribe("capability.executed", capability_events.append)
    bus.subscribe("conversation.reply", replies.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "What time is it?", "request_id": "req-low"},
            source="test",
        )
    )

    assert len(policy_events) == 1
    assert policy_events[0].payload["allowed"] is True
    assert policy_events[0].payload["code"] == "ALLOW"
    assert len(capability_events) == 1
    assert capability_events[0].payload["capability"] == "get_time"
    assert len(replies) == 1
    assert "get_time=" in str(replies[0].payload["reply_text"])


def test_high_risk_capability_requires_separate_confirmation_event() -> None:
    bus, _, _ = build_runtime(config=RuntimeConfig(require_user_confirmation_for_high_risk=True))
    policy_events: list[Event] = []
    capability_events: list[Event] = []
    confirmation_events: list[Event] = []

    bus.subscribe("policy.decision", policy_events.append)
    bus.subscribe("capability.executed", capability_events.append)
    bus.subscribe("capability.confirmation_required", confirmation_events.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "unlock the door", "request_id": "req-1"},
            source="test",
        )
    )

    assert len(policy_events) == 1
    assert policy_events[0].payload["allowed"] is False
    assert policy_events[0].payload["code"] == "CONFIRM_REQUIRED"
    assert capability_events == []
    assert len(confirmation_events) == 1
    assert confirmation_events[0].payload["request_id"] == "req-1"

    bus.publish(Event(name="capability.confirmation_granted", payload={"request_id": "req-1"}, source="test"))

    assert len(policy_events) == 2
    assert policy_events[1].payload["allowed"] is True
    assert policy_events[1].payload["code"] == "ALLOW"
    assert len(capability_events) == 1
    assert capability_events[0].payload["capability"] == "unlock_door"


def test_high_risk_capability_does_not_execute_when_confirmation_denied() -> None:
    bus, _, _ = build_runtime(config=RuntimeConfig(require_user_confirmation_for_high_risk=True))
    capability_events: list[Event] = []
    replies: list[Event] = []

    bus.subscribe("capability.executed", capability_events.append)
    bus.subscribe("conversation.reply", replies.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "unlock the door", "request_id": "req-deny"},
            source="test",
        )
    )
    bus.publish(
        Event(
            name="capability.confirmation_denied",
            payload={"request_id": "req-deny"},
            source="test",
        )
    )

    assert capability_events == []
    assert len(replies) == 2
    assert "will not run" in str(replies[-1].payload["reply_text"]).lower()


def test_high_risk_capability_allowed_when_confirmation_not_required() -> None:
    bus, _, _ = build_runtime(config=RuntimeConfig(require_user_confirmation_for_high_risk=False))
    policy_events: list[Event] = []
    capability_events: list[Event] = []

    bus.subscribe("policy.decision", policy_events.append)
    bus.subscribe("capability.executed", capability_events.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "unlock the door", "request_id": "req-2"},
            source="test",
        )
    )

    assert len(policy_events) == 1
    assert policy_events[0].payload["allowed"] is True
    assert policy_events[0].payload["code"] == "ALLOW"
    assert len(capability_events) == 1
    assert capability_events[0].payload["capability"] == "unlock_door"


def test_schema_invalid_arguments_block_execution() -> None:
    bus, _, _ = build_runtime(llm_provider=InvalidArgsLLMProvider())
    policy_events: list[Event] = []
    capability_events: list[Event] = []

    bus.subscribe("policy.decision", policy_events.append)
    bus.subscribe("capability.executed", capability_events.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "time", "request_id": "req-schema"},
            source="test",
        )
    )

    assert len(policy_events) == 2
    assert policy_events[0].payload["code"] == "ALLOW"
    assert policy_events[1].payload["code"] == "SCHEMA_INVALID"
    assert capability_events == []


def test_offline_mode_blocks_network_llm_provider() -> None:
    bus, _, _ = build_runtime(
        config=RuntimeConfig(offline_mode=True),
        llm_provider=NetworkLLMProvider(),
    )
    replies: list[Event] = []
    bus.subscribe("conversation.reply", replies.append)

    bus.publish(Event(name="conversation.received", payload={"prompt": "hello"}, source="test"))

    assert len(replies) == 1
    assert "offline mode" in str(replies[0].payload["reply_text"]).lower()


def test_pending_confirmation_expires_after_ttl() -> None:
    bus, _, executor = build_runtime(config=RuntimeConfig(confirmation_ttl_seconds=1))
    expired: list[Event] = []
    bus.subscribe("capability.confirmation_expired", expired.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "unlock the door", "request_id": "req-expire"},
            source="test",
        )
    )

    pending = executor._pending_confirmations["req-expire"]
    pending.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    executor._pending_confirmations["req-expire"] = pending

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "hello", "request_id": "req-trigger-expiry"},
            source="test",
        )
    )

    assert len(expired) == 1
    assert expired[0].payload["request_id"] == "req-expire"


def test_runtime_wires_escalation_engine() -> None:
    bus, _, _ = build_runtime()
    decisions: list[Event] = []
    bus.subscribe("escalation.decision", decisions.append)

    bus.publish(
        Event(
            name="risk.signal",
            payload={"severity": "ORANGE", "reason_code": "CONFUSION", "summary": "Need check-in"},
            source="test",
        )
    )

    assert len(decisions) == 1
    assert decisions[0].payload["severity"] == "ORANGE"
    assert decisions[0].payload["reason_code"] == "CONFUSION"


def test_executor_emits_concern_detected_event_from_llm_response() -> None:
    bus, _, _ = build_runtime()
    concern_events: list[Event] = []
    bus.subscribe("concern.detected", concern_events.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "I am confused and scared", "request_id": "req-concern"},
            source="test",
        )
    )

    assert len(concern_events) == 1
    assert concern_events[0].payload["level"] == "ORANGE"
    assert concern_events[0].payload["reason_code"] == "CONFUSION"
    assert concern_events[0].payload["request_id"] == "req-concern"


def test_concern_detected_triggers_escalation_decision() -> None:
    bus, _, _ = build_runtime()
    decisions: list[Event] = []
    bus.subscribe("escalation.decision", decisions.append)

    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": "help me now", "request_id": "req-red"},
            source="test",
        )
    )

    assert len(decisions) >= 1
    assert decisions[-1].payload["severity"] == "RED"
