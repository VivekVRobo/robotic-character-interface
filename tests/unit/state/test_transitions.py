import pytest

from rci.domain.enums import SystemState
from rci.state.transitions import InvalidStateTransition, allowed_targets, validate_transition


def test_nominal_boot_transition_is_allowed() -> None:
    validate_transition(SystemState.BOOT, SystemState.SELF_TEST)


def test_boot_cannot_skip_directly_to_armed() -> None:
    with pytest.raises(InvalidStateTransition, match="BOOT -> ARMED"):
        validate_transition(SystemState.BOOT, SystemState.ARMED)


def test_same_state_transition_is_not_implicitly_allowed() -> None:
    with pytest.raises(InvalidStateTransition):
        validate_transition(SystemState.IDLE, SystemState.IDLE)


def test_shutdown_is_terminal() -> None:
    assert allowed_targets(SystemState.SHUTDOWN) == frozenset()


def test_estop_recovery_requires_self_test_or_shutdown() -> None:
    assert allowed_targets(SystemState.ESTOP) == frozenset(
        {SystemState.SELF_TEST, SystemState.SHUTDOWN}
    )
