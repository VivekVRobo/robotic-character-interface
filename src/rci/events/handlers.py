"""Handler and subscription types for the event bus."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID, uuid4

from rci.events.base import Event

EventHandler = Callable[[Event], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class Subscription:
    """Opaque subscription token used for deterministic unsubscription."""

    subscription_id: UUID
    event_type: type[Event]

    @classmethod
    def create(cls, event_type: type[Event]) -> Subscription:
        return cls(subscription_id=uuid4(), event_type=event_type)


@dataclass(frozen=True, slots=True)
class HandlerFailure:
    event_id: UUID
    event_type: str
    subscription_id: UUID
    handler_name: str
    error_type: str
    message: str
