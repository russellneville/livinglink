from livinglink.core.event_bus import EventBus
from livinglink.core.events import Event


def test_event_bus_publish_invokes_subscribers() -> None:
    bus = EventBus()
    received: list[str] = []

    def handler(event: Event) -> None:
        received.append(event.payload["value"])

    bus.subscribe("sample", handler)
    count = bus.publish(Event(name="sample", payload={"value": "ok"}))

    assert count == 1
    assert received == ["ok"]
