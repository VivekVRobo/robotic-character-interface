"""Deterministic JSON serialization for registered event types."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from rci.domain.errors import ProtocolError
from rci.events.base import Event
from rci.events.types import (
    CharacterActivated,
    EmergencyStopTriggered,
    FaultDetected,
    GestureDetected,
    HealthChanged,
    SystemStarted,
    SystemStateChanged,
    TrajectoryRejected,
)

BUILTIN_EVENT_TYPES: tuple[type[Event], ...] = (
    SystemStarted,
    SystemStateChanged,
    HealthChanged,
    GestureDetected,
    CharacterActivated,
    TrajectoryRejected,
    EmergencyStopTriggered,
    FaultDetected,
)


class EventSerializer:
    """Serialize/deserialize events using an explicit type registry."""

    def __init__(self, event_types: Iterable[type[Event]] = BUILTIN_EVENT_TYPES) -> None:
        self._registry: dict[str, type[Event]] = {}
        for event_type in event_types:
            self.register(event_type)

    def register(self, event_type: type[Event]) -> None:
        """Register one type and reject discriminator collisions."""
        discriminator = event_type.model_fields["event_type"].default
        if not isinstance(discriminator, str) or not discriminator:
            raise ValueError("event type must define a non-empty event_type default")

        existing = self._registry.get(discriminator)
        if existing is not None and existing is not event_type:
            raise ValueError(f"event_type discriminator already registered: {discriminator}")
        self._registry[discriminator] = event_type

    def dumps(self, event: Event) -> str:
        return event.model_dump_json()

    def loads(self, payload: str) -> Event:
        try:
            raw: Any = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ProtocolError("invalid event JSON") from exc

        if not isinstance(raw, dict):
            raise ProtocolError("serialized event must be a JSON object")

        discriminator = raw.get("event_type")
        if not isinstance(discriminator, str):
            raise ProtocolError("serialized event is missing event_type")

        event_type = self._registry.get(discriminator)
        if event_type is None:
            raise ProtocolError(f"unknown event_type: {discriminator}")

        try:
            return event_type.model_validate(raw)
        except ValidationError as exc:
            raise ProtocolError(f"invalid {discriminator} event payload") from exc
