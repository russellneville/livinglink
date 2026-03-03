from __future__ import annotations

from livinglink.providers.llm.base import ActionRequest, LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Simple rule-based model substitute for Phase 1 runtime wiring."""

    requires_network = False

    def generate(self, prompt: str) -> LLMResponse:
        lowered = prompt.lower()

        if "help" in lowered or "fall" in lowered:
            return LLMResponse(
                reply_text="I hear urgency. I will prepare a safety check.",
                requested_actions=[],
                concern_level="RED",
                concern_reason_code="DISTRESS",
            )

        if "confused" in lowered or "lost" in lowered or "scared" in lowered:
            return LLMResponse(
                reply_text="I understand this feels difficult. Let us check in calmly.",
                requested_actions=[],
                concern_level="ORANGE",
                concern_reason_code="CONFUSION",
            )

        if "time" in lowered:
            return LLMResponse(
                reply_text="Let me check the time.",
                requested_actions=[ActionRequest(name="get_time", arguments={})],
            )

        if "unlock" in lowered:
            return LLMResponse(
                reply_text="I can process that request.",
                requested_actions=[ActionRequest(name="unlock_door", arguments={})],
            )

        return LLMResponse(reply_text=f"I heard: {prompt}", requested_actions=[])
