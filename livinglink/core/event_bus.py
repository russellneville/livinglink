from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Callable

from livinglink.core.events import Event

EventHandler = Callable[[Event], None]


class EventBus:
    """In-memory event bus for composing modules without tight coupling."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        with self._lock:
            self._subscriptions[event_name].append(handler)

    def publish(self, event: Event) -> int:
        with self._lock:
            handlers = list(self._subscriptions.get(event.name, []))
        for handler in handlers:
            handler(event)
        return len(handlers)
