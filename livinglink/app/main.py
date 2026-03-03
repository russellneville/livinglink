from __future__ import annotations

from livinglink.care.contacts import ContactBook
from livinglink.care.escalation import EscalationEngine
from livinglink.care.notifications import InMemoryConnector, NotificationDispatcher
from livinglink.core.config import RuntimeConfig
from livinglink.core.executor import ConversationExecutor, default_capability_handlers
from livinglink.core.event_bus import EventBus
from livinglink.core.events import Event
from livinglink.providers.llm.base import LLMProvider
from livinglink.providers.llm.mock import MockLLMProvider
from livinglink.providers.stt.mock import MockSTTProvider
from livinglink.providers.tts.base import TTSProvider
from livinglink.providers.tts.mock import MockTTSProvider
from livinglink.safety.capabilities import Capability, CapabilityRegistry, RiskLevel
from livinglink.safety.policy_gate import PolicyGate


CAPABILITY_DEFINITIONS: tuple[tuple[str, RiskLevel, dict], ...] = (
    ("get_time", RiskLevel.LOW, {"type": "object", "properties": {}, "additionalProperties": False}),
    ("unlock_door", RiskLevel.HIGH, {"type": "object", "properties": {}, "additionalProperties": False}),
)


def _build_care_engine(bus: EventBus, config: RuntimeConfig) -> EscalationEngine:
    contacts = ContactBook()
    dispatcher = NotificationDispatcher(
        connectors={
            "email": InMemoryConnector("email"),
            "webhook": InMemoryConnector("webhook"),
        },
        throttle_seconds=config.notification_throttle_seconds,
    )
    engine = EscalationEngine(
        bus=bus,
        contacts=contacts,
        notifications=dispatcher,
        auto_ems=config.auto_ems_enabled,
        pending_ttl_seconds=config.emergency_pending_ttl_seconds,
    )
    engine.start()
    return engine


def build_runtime(
    config: RuntimeConfig | None = None,
    llm_provider: LLMProvider | None = None,
    tts_provider: TTSProvider | None = None,
) -> tuple[EventBus, PolicyGate, ConversationExecutor]:
    config = config or RuntimeConfig()
    llm_provider = llm_provider or MockLLMProvider()
    tts_provider = tts_provider or MockTTSProvider()
    _ = MockSTTProvider()

    bus = EventBus()
    registry = CapabilityRegistry()
    capability_schemas: dict[str, dict] = {}
    for capability_name, risk_level, schema in CAPABILITY_DEFINITIONS:
        registry.register(
            Capability(
                name=capability_name,
                risk_level=risk_level,
                schema=schema,
            )
        )
        capability_schemas[capability_name] = schema

    gate = PolicyGate(registry)
    executor = ConversationExecutor(
        bus=bus,
        policy_gate=gate,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        config=config,
        capability_handlers=default_capability_handlers(),
        capability_schemas=capability_schemas,
    )
    executor.start()
    _ = _build_care_engine(bus, config)
    return bus, gate, executor


def demo_round_trip(prompt: str, request_id: str = "demo-request-1", confirm: bool = False) -> str:
    bus, _, _ = build_runtime()
    replies: list[str] = []
    bus.subscribe("conversation.reply", lambda event: replies.append(str(event.payload["reply_text"])))
    bus.publish(
        Event(
            name="conversation.received",
            payload={"prompt": prompt, "request_id": request_id},
            source="user",
        )
    )
    if confirm:
        bus.publish(
            Event(
                name="capability.confirmation_granted",
                payload={"request_id": request_id},
                source="user",
            )
        )
    return replies[-1] if replies else ""


if __name__ == "__main__":
    print(demo_round_trip("Hello LivingLink"))
