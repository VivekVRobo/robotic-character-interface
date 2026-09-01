"""Base event models and event-system errors."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from rci.domain.identifiers import InteractionId, new_event_id
from rci.domain.timestamps import monotonic_now_ns, utc_now


class EventPriority(IntEnum):
    """Lower numeric values are dispatched before higher values."""

    CRITICAL = 0
    HIGH = 10
    NORMAL = 20
    LOW = 30


class Event(BaseModel):
    """Immutable, traceable base event shared by all runtime subsystems."""

    model_config = ConfigDict(frozen=True)

    event_type: str = "event"
    event_id: UUID = Field(default_factory=new_event_id)
    interaction_id: InteractionId | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    monotonic_ns: int = Field(default_factory=monotonic_now_ns, ge=0)
    source: str = Field(min_length=1)


class BusLifecycleEvent(Event):
    """Internal event category reserved for future bus lifecycle telemetry."""

    event_type: Literal["bus.lifecycle"] = "bus.lifecycle"


class EventBusError(RuntimeError):
    """Base class for event-bus lifecycle/queue failures."""


class EventBusNotRunning(EventBusError):
    """Raised when publishing to a bus that has not been started."""


class EventQueueFull(EventBusError):
    """Raised by non-blocking publish when bounded capacity is exhausted."""
