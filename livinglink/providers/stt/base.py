from __future__ import annotations

from typing import Protocol


class STTProvider(Protocol):
    def transcribe(self, audio_bytes: bytes) -> str:
        ...
