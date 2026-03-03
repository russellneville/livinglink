from __future__ import annotations

from livinglink.providers.tts.base import TTSProvider


class MockTTSProvider(TTSProvider):
    """Deterministic TTS provider for local integration tests."""

    def synthesize(self, text: str) -> bytes:
        return text.encode("utf-8")
