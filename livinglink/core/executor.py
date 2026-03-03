from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from livinglink.core.config import RuntimeConfig
from livinglink.core.event_bus import EventBus
from livinglink.core.events import Event
from livinglink.providers.llm.base import ActionRequest, LLMProvider
from livinglink.providers.tts.base import TTSProvider
from livinglink.safety.policy_gate import PolicyGate
from livinglink.safety.schema_validation import validate_object_schema

CapabilityHandler = Callable[[dict], str]


@dataclass(slots=True)
class PendingConfirmation:
    request_id: str
    created_at: datetime
    reply_text: str
    actions: list[ActionRequest]
    consents: set[str]


@dataclass(slots=True)
class ConversationExecutor:
    """Executes conversation events through safety gate and capabilities."""

    bus: EventBus
    policy_gate: PolicyGate
    llm_provider: LLMProvider
    tts_provider: TTSProvider
    config: RuntimeConfig
    capability_handlers: dict[str, CapabilityHandler]
    capability_schemas: dict[str, dict]
    _pending_confirmations: dict[str, PendingConfirmation] = field(init=False, default_factory=dict)

    def start(self) -> None:
        self.bus.subscribe("conversation.received", self._on_conversation_received)
        self.bus.subscribe("capability.confirmation_granted", self._on_confirmation_granted)
        self.bus.subscribe("capability.confirmation_denied", self._on_confirmation_denied)

    def _on_conversation_received(self, event: Event) -> None:
        self._expire_pending_confirmations()

        request_id = str(event.payload.get("request_id") or uuid4())
        prompt = str(event.payload.get("prompt", "")).strip()
        consents = set(event.payload.get("consents", []))

        if not prompt:
            self._publish_reply("I did not catch that. Please try again.", request_id, [])
            return

        if self.config.offline_mode and bool(getattr(self.llm_provider, "requires_network", False)):
            self._publish_reply("I am in offline mode right now. Please try again later.", request_id, [])
            return

        try:
            response = self.llm_provider.generate(prompt)
        except Exception as exc:
            self._publish_error("provider.error", "llm", str(exc), request_id)
            self._publish_reply("I had trouble processing that request. Please try again.", request_id, [])
            return

        actions = response.requested_actions
        if response.concern_level:
            self.bus.publish(
                Event(
                    name="concern.detected",
                    payload={
                        "level": response.concern_level,
                        "reason_code": response.concern_reason_code,
                        "context": prompt,
                        "request_id": request_id,
                        "trigger": "llm_response",
                    },
                    source="executor",
                )
            )
        executed, pending = self._process_actions(
            actions=actions,
            request_id=request_id,
            consents=consents,
            user_confirmed=False,
        )

        if pending:
            self._pending_confirmations[request_id] = PendingConfirmation(
                request_id=request_id,
                created_at=datetime.now(timezone.utc),
                reply_text=response.reply_text,
                actions=pending,
                consents=consents,
            )
            for action in pending:
                self.bus.publish(
                    Event(
                        name="capability.confirmation_required",
                        payload={
                            "request_id": request_id,
                            "capability_name": action.name,
                            "display_message": f"Please confirm the action: {action.name}",
                        },
                        source="executor",
                    )
                )

        reply_text = self._with_results(response.reply_text, executed)
        self._publish_reply(reply_text, request_id, actions)

    def _on_confirmation_granted(self, event: Event) -> None:
        self._expire_pending_confirmations()

        request_id = str(event.payload.get("request_id", "")).strip()
        if not request_id:
            self._publish_error("confirmation.error", "confirmation", "MISSING_REQUEST_ID", request_id)
            return

        pending = self._pending_confirmations.pop(request_id, None)
        if pending is None:
            self._publish_error("confirmation.error", "confirmation", "UNKNOWN_REQUEST_ID", request_id)
            return

        executed, _ = self._process_actions(
            actions=pending.actions,
            request_id=request_id,
            consents=pending.consents,
            user_confirmed=True,
        )

        reply_text = self._with_results(pending.reply_text, executed)
        self._publish_reply(reply_text, request_id, pending.actions)

    def _on_confirmation_denied(self, event: Event) -> None:
        self._expire_pending_confirmations()

        request_id = str(event.payload.get("request_id", "")).strip()
        if not request_id:
            self._publish_error("confirmation.error", "confirmation", "MISSING_REQUEST_ID", request_id)
            return

        pending = self._pending_confirmations.pop(request_id, None)
        if pending is None:
            self._publish_error("confirmation.error", "confirmation", "UNKNOWN_REQUEST_ID", request_id)
            return

        self._publish_reply(
            "Okay, I will not run that action.",
            request_id,
            pending.actions,
        )

    def _process_actions(
        self,
        actions: list[ActionRequest],
        request_id: str,
        consents: set[str],
        user_confirmed: bool,
    ) -> tuple[dict[str, str], list[ActionRequest]]:
        executed: dict[str, str] = {}
        pending: list[ActionRequest] = []

        for action in actions:
            decision = self.policy_gate.evaluate(
                capability_name=action.name,
                granted_consents=consents,
                user_confirmed=user_confirmed or not self.config.require_user_confirmation_for_high_risk,
            )
            self._publish_policy_decision(action.name, decision.allowed, decision.reason_code, request_id)

            if not decision.allowed:
                if decision.reason_code == "CONFIRM_REQUIRED" and not user_confirmed:
                    pending.append(action)
                continue

            schema = self.capability_schemas.get(action.name)
            if schema is None:
                self._publish_policy_decision(action.name, False, "SCHEMA_MISSING", request_id)
                continue

            valid, reason = validate_object_schema(schema, action.arguments)
            if not valid:
                self._publish_policy_decision(action.name, False, "SCHEMA_INVALID", request_id)
                self._publish_error("capability.error", action.name, reason, request_id)
                continue

            handler = self.capability_handlers.get(action.name)
            if handler is None:
                self.bus.publish(
                    Event(
                        name="capability.skipped",
                        payload={"capability": action.name, "reason": "NO_HANDLER", "request_id": request_id},
                        source="executor",
                    )
                )
                continue

            try:
                result = handler(action.arguments)
            except Exception as exc:
                self._publish_error("capability.error", action.name, str(exc), request_id)
                continue

            executed[action.name] = result
            self.bus.publish(
                Event(
                    name="capability.executed",
                    payload={"capability": action.name, "result": result, "request_id": request_id},
                    source="executor",
                )
            )

        return executed, pending

    def _publish_policy_decision(self, capability: str, allowed: bool, code: str, request_id: str) -> None:
        self.bus.publish(
            Event(
                name="policy.decision",
                payload={
                    "capability": capability,
                    "allowed": allowed,
                    "code": code,
                    "request_id": request_id,
                },
                source="policy_gate",
            )
        )

    def _with_results(self, base: str, executed: dict[str, str]) -> str:
        if not executed:
            return base

        suffix = "; ".join(f"{name}={value}" for name, value in executed.items())
        return f"{base} [{suffix}]"

    def _publish_error(self, event_name: str, component: str, error: str, request_id: str) -> None:
        self.bus.publish(
            Event(
                name=event_name,
                payload={"component": component, "error": error, "request_id": request_id},
                source="executor",
            )
        )

    def _publish_reply(self, reply_text: str, request_id: str, actions: list[ActionRequest]) -> None:
        try:
            audio_bytes = self.tts_provider.synthesize(reply_text)
        except Exception as exc:
            self._publish_error("provider.error", "tts", str(exc), request_id)
            audio_bytes = b""

        self.bus.publish(
            Event(
                name="conversation.reply",
                payload={
                    "request_id": request_id,
                    "reply_text": reply_text,
                    "audio_bytes": audio_bytes,
                    "requested_actions": [
                        {"name": action.name, "arguments": action.arguments} for action in actions
                    ],
                },
                source="executor",
            )
        )

    def _expire_pending_confirmations(self) -> None:
        if not self._pending_confirmations:
            return

        ttl = timedelta(seconds=self.config.confirmation_ttl_seconds)
        now = datetime.now(timezone.utc)
        expired: list[str] = []
        for request_id, pending in self._pending_confirmations.items():
            if (now - pending.created_at) > ttl:
                expired.append(request_id)

        for request_id in expired:
            pending = self._pending_confirmations.pop(request_id)
            self.bus.publish(
                Event(
                    name="capability.confirmation_expired",
                    payload={
                        "request_id": request_id,
                        "capabilities": [action.name for action in pending.actions],
                    },
                    source="executor",
                )
            )


def default_capability_handlers() -> dict[str, CapabilityHandler]:
    def get_time(_: dict) -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%H:%M UTC")

    def unlock_door(_: dict) -> str:
        return "SIMULATION_ONLY"

    return {
        "get_time": get_time,
        "unlock_door": unlock_door,
    }
