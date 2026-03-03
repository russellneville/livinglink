from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Event:
    """Typed event envelope for internal publish/subscribe flows."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid4()))
