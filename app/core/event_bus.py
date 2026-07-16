"""Platform-wide event bus foundation.

Per `PROJECT_VISION.md`'s Event Driven Architecture principle: major
modules should communicate through events instead of tight coupling
whenever practical, and future engines should be able to subscribe
without modifying existing modules.

This module ships the bus mechanism only -- no business events are
defined or published here. Concrete event names/payloads belong to
whichever future phase introduces them.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.exceptions import NotImplementedYetError
from app.utils.logger import get_logger

logger = get_logger(__name__)

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A published occurrence: a name, a payload, and when it happened."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """A minimal synchronous publish/subscribe bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register `handler` to be called whenever `event_name` is published."""
        self._subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered `handler` for `event_name`.

        Raises:
            ValueError: if `handler` was not subscribed to `event_name`.
        """
        try:
            self._subscribers[event_name].remove(handler)
        except ValueError as exc:
            raise ValueError(
                f"Handler {handler!r} is not subscribed to event {event_name!r}."
            ) from exc

    def publish(self, event_name: str, payload: dict[str, Any] | None = None) -> Event:
        """Publish `event_name` synchronously to every current subscriber.

        A handler raising an exception is logged and does not prevent
        other subscribers from receiving the event.
        """
        event = Event(name=event_name, payload=payload or {})
        for handler in list(self._subscribers.get(event_name, ())):
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler for %r raised an exception", event_name)
        return event

    def subscriber_count(self, event_name: str) -> int:
        """Return how many handlers are currently subscribed to `event_name`."""
        return len(self._subscribers.get(event_name, ()))

    async def publish_async(self, event_name: str, payload: dict[str, Any] | None = None) -> Event:
        """Reserved for future asynchronous dispatch. Not implemented yet."""
        raise NotImplementedYetError("EventBus.publish_async", phase="a future phase (async event support)")
