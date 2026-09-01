"""Canonical legal system-state transition table."""

from typing import Final

from rci.domain.enums import SystemState
from rci.domain.errors import RCIError


class InvalidStateTransition(RCIError):
    """Raised when a component requests a transition outside the state machine."""


LEGAL_TRANSITIONS: Final[dict[SystemState, frozenset[SystemState]]] = {
    SystemState.BOOT: frozenset(
        {SystemState.SELF_TEST, SystemState.FAULT, SystemState.ESTOP, SystemState.SHUTDOWN}
    ),
    SystemState.SELF_TEST: frozenset(
        {
            SystemState.CALIBRATING,
            SystemState.DEGRADED,
            SystemState.FAULT,
            SystemState.ESTOP,
            SystemState.SHUTDOWN,
        }
    ),
    SystemState.CALIBRATING: frozenset(
        {
            SystemState.IDLE,
            SystemState.DEGRADED,
            SystemState.FAULT,
            SystemState.ESTOP,
            SystemState.SHUTDOWN,
        }
    ),
    SystemState.IDLE: frozenset(
        {
            SystemState.ARMED,
            SystemState.CALIBRATING,
            SystemState.DEGRADED,
            SystemState.FAULT,
            SystemState.ESTOP,
            SystemState.SHUTDOWN,
        }
    ),
    SystemState.ARMED: frozenset(
        {
            SystemState.EXECUTING,
            SystemState.IDLE,
            SystemState.DEGRADED,
            SystemState.FAULT,
            SystemState.ESTOP,
            SystemState.SHUTDOWN,
        }
    ),
    SystemState.EXECUTING: frozenset(
        {
            SystemState.ARMED,
            SystemState.DEGRADED,
            SystemState.FAULT,
            SystemState.ESTOP,
            SystemState.SHUTDOWN,
        }
    ),
    SystemState.DEGRADED: frozenset(
        {
            SystemState.SELF_TEST,
            SystemState.IDLE,
            SystemState.FAULT,
            SystemState.ESTOP,
            SystemState.SHUTDOWN,
        }
    ),
    SystemState.FAULT: frozenset({SystemState.SELF_TEST, SystemState.ESTOP, SystemState.SHUTDOWN}),
    SystemState.ESTOP: frozenset({SystemState.SELF_TEST, SystemState.SHUTDOWN}),
    SystemState.SHUTDOWN: frozenset(),
}


def allowed_targets(state: SystemState) -> frozenset[SystemState]:
    return LEGAL_TRANSITIONS[state]


def can_transition(current: SystemState, target: SystemState) -> bool:
    return target in LEGAL_TRANSITIONS[current]


def validate_transition(current: SystemState, target: SystemState) -> None:
    if not can_transition(current, target):
        message = f"illegal system transition: {current.value} -> {target.value}"
        raise InvalidStateTransition(message)
