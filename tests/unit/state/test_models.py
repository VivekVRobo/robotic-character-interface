import pytest
from pydantic import ValidationError

from rci.state.models import GestureSnapshot, StateSnapshot


def test_default_state_is_safe_and_booted() -> None:
    snapshot = StateSnapshot()
    assert snapshot.system.state.value == "BOOT"
    assert snapshot.safety.estop_active is False
    assert snapshot.safety.motion_authorized is False
    assert snapshot.robot.connected is False


def test_gesture_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        GestureSnapshot(confidence=1.1)


def test_snapshot_is_immutable() -> None:
    snapshot = StateSnapshot()
    with pytest.raises(ValidationError):
        snapshot.revision = 10  # type: ignore[misc]
