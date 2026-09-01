from datetime import datetime

import pytest
from pydantic import ValidationError

from rci.events.base import Event


def test_event_defaults_are_traceable() -> None:
    event = Event(source="test")
    assert event.event_id is not None
    assert isinstance(event.timestamp, datetime)
    assert event.monotonic_ns >= 0


def test_event_source_cannot_be_empty() -> None:
    with pytest.raises(ValidationError):
        Event(source="")


def test_event_is_immutable() -> None:
    event = Event(source="test")
    with pytest.raises(ValidationError):
        event.source = "changed"  # type: ignore[misc]
