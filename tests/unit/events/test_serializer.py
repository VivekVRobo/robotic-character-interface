import pytest

from rci.domain.enums import SystemState
from rci.domain.errors import ProtocolError
from rci.events.serializer import EventSerializer
from rci.events.types import SystemStateChanged


def test_round_trip_preserves_typed_event() -> None:
    serializer = EventSerializer()
    original = SystemStateChanged(
        source="system-controller",
        previous_state=SystemState.BOOT,
        current_state=SystemState.SELF_TEST,
        reason="startup",
    )

    decoded = serializer.loads(serializer.dumps(original))

    assert isinstance(decoded, SystemStateChanged)
    assert decoded == original


def test_unknown_event_type_is_rejected() -> None:
    serializer = EventSerializer()
    with pytest.raises(ProtocolError, match="unknown event_type"):
        serializer.loads('{"event_type":"unknown","source":"test"}')


def test_invalid_json_is_rejected() -> None:
    serializer = EventSerializer()
    with pytest.raises(ProtocolError, match="invalid event JSON"):
        serializer.loads("{")
