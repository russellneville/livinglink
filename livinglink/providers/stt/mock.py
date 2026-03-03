from __future__ import annotations

from livinglink.providers.stt.base import STTProvider


class MockSTTProvider(STTProvider):
    """Deterministic STT provider for local integration tests."""

    def __init__(self, default_transcript: str = "Hello LivingLink") -> None:
        self._default_transcript = default_transcript

    def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return self._default_transcript

        try:
            decoded = audio_bytes.decode("utf-8").strip()
            return decoded or self._default_transcript
        except UnicodeDecodeError:
            return self._default_transcript
