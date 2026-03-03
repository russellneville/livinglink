from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ActionRequest:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    reply_text: str
    requested_actions: list[ActionRequest] = field(default_factory=list)
    concern_level: str | None = None
    concern_reason_code: str = "UNSPECIFIED"


class LLMProvider:
    def generate(self, prompt: str) -> LLMResponse:
        # Placeholder model behavior for early integration.
        return LLMResponse(reply_text=f"I heard: {prompt}", requested_actions=[])
