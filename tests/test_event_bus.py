"""Tests for app.core.event_bus."""

import asyncio

import pytest

from app.core.event_bus import Event, EventBus
from app.core.exceptions import NotImplementedYetError


def test_publish_calls_subscribed_handler() -> None:
    bus = EventBus()
    received = []
    bus.subscribe("topic", received.append)

    event = bus.publish("topic", {"a": 1})

    assert len(received) == 1
    assert received[0] is event
    assert event.name == "topic"
    assert event.payload == {"a": 1}


def test_publish_with_no_subscribers_does_not_raise() -> None:
    bus = EventBus()
    event = bus.publish("nobody-listening")
    assert event.name == "nobody-listening"


def test_multiple_subscribers_all_receive_event() -> None:
    bus = EventBus()
    calls = []
    bus.subscribe("topic", lambda e: calls.append("one"))
    bus.subscribe("topic", lambda e: calls.append("two"))

    bus.publish("topic")

    assert calls == ["one", "two"]


def test_unsubscribe_stops_future_delivery() -> None:
    bus = EventBus()
    received = []
    handler = received.append
    bus.subscribe("topic", handler)
    bus.unsubscribe("topic", handler)

    bus.publish("topic")

    assert received == []


def test_unsubscribe_unknown_handler_raises() -> None:
    bus = EventBus()
    with pytest.raises(ValueError):
        bus.unsubscribe("topic", lambda e: None)


def test_subscriber_count() -> None:
    bus = EventBus()
    assert bus.subscriber_count("topic") == 0
    bus.subscribe("topic", lambda e: None)
    assert bus.subscriber_count("topic") == 1


def test_failing_handler_does_not_block_other_subscribers() -> None:
    bus = EventBus()
    received = []

    def bad_handler(event: Event) -> None:
        raise RuntimeError("boom")

    bus.subscribe("topic", bad_handler)
    bus.subscribe("topic", received.append)

    bus.publish("topic")  # must not raise

    assert len(received) == 1


def test_events_for_different_topics_are_isolated() -> None:
    bus = EventBus()
    received = []
    bus.subscribe("topic_a", received.append)

    bus.publish("topic_b")

    assert received == []


def test_publish_async_is_not_implemented_yet() -> None:
    bus = EventBus()
    with pytest.raises(NotImplementedYetError):
        asyncio.run(bus.publish_async("topic"))
