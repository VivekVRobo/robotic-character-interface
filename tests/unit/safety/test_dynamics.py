from math import nan

from rci.domain.enums import MotionDecision, SystemState
from rci.safety.dynamics import assess_dynamic_motion_eligibility
from rci.safety.models import (
    CartesianPoint,
    JointConstraint,
    MotionCandidate,
    MotionDynamics,
    MotionSafetyPolicy,
    SafetyEnvelope,
    SafetyViolationCode,
    WorkspaceBounds,
)


def _envelope() -> SafetyEnvelope:
    return SafetyEnvelope(
        joints={
            "base": JointConstraint("base", -90.0, 90.0, 0.0, True),
            "shoulder": JointConstraint("shoulder", -45.0, 120.0, 20.0, True),
        },
        workspace=WorkspaceBounds(
            -300.0,
            300.0,
            -300.0,
            300.0,
            0.0,
            500.0,
            True,
        ),
        allowed_states=frozenset({SystemState.ARMED, SystemState.EXECUTING}),
        robot_verified=True,
        servos_verified=True,
        motion_policy=MotionSafetyPolicy(
            command_ttl_ms=250.0,
            heartbeat_timeout_ms=500.0,
            max_velocity_deg_s=60.0,
            max_acceleration_deg_s2=180.0,
        ),
    )


def _candidate() -> MotionCandidate:
    return MotionCandidate(
        system_state=SystemState.ARMED,
        estop_active=False,
        joint_targets_deg={"base": 0.0, "shoulder": 20.0},
        workspace_point_mm=CartesianPoint(100.0, 0.0, 200.0),
    )


def _dynamics(**overrides: object) -> MotionDynamics:
    values: dict[str, object] = {
        "command_age_ms": 10.0,
        "heartbeat_age_ms": 20.0,
        "joint_velocities_deg_s": {"base": 5.0, "shoulder": -5.0},
        "joint_accelerations_deg_s2": {"base": 10.0, "shoulder": -10.0},
    }
    values.update(overrides)
    return MotionDynamics(**values)  # type: ignore[arg-type]


def _codes(result: object) -> set[SafetyViolationCode]:
    return {violation.code for violation in result.violations}  # type: ignore[attr-defined]


def test_dynamic_limits_are_inclusive_at_policy_boundaries() -> None:
    dynamics = MotionDynamics(
        command_age_ms=250.0,
        heartbeat_age_ms=500.0,
        joint_velocities_deg_s={"base": 60.0, "shoulder": -60.0},
        joint_accelerations_deg_s2={"base": 180.0, "shoulder": -180.0},
    )

    result = assess_dynamic_motion_eligibility(_envelope(), _candidate(), dynamics)

    assert result.decision is MotionDecision.APPROVE
    assert result.approved


def test_stale_command_is_rejected() -> None:
    result = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(command_age_ms=250.001),
    )

    assert SafetyViolationCode.COMMAND_STALE in _codes(result)


def test_stale_heartbeat_is_rejected() -> None:
    result = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(heartbeat_age_ms=500.001),
    )

    assert SafetyViolationCode.HEARTBEAT_STALE in _codes(result)


def test_negative_or_nonfinite_ages_are_rejected() -> None:
    negative = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(command_age_ms=-1.0),
    )
    nonfinite = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(heartbeat_age_ms=nan),
    )

    assert SafetyViolationCode.COMMAND_AGE_INVALID in _codes(negative)
    assert SafetyViolationCode.HEARTBEAT_AGE_INVALID in _codes(nonfinite)


def test_missing_dynamic_samples_are_rejected() -> None:
    result = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(
            joint_velocities_deg_s={"base": 1.0},
            joint_accelerations_deg_s2={"shoulder": 1.0},
        ),
    )

    assert SafetyViolationCode.VELOCITY_SAMPLE_MISSING in _codes(result)
    assert SafetyViolationCode.ACCELERATION_SAMPLE_MISSING in _codes(result)


def test_velocity_limit_violation_is_rejected() -> None:
    result = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(joint_velocities_deg_s={"base": 60.001, "shoulder": 0.0}),
    )

    assert SafetyViolationCode.VELOCITY_LIMIT_VIOLATION in _codes(result)


def test_acceleration_limit_violation_is_rejected() -> None:
    result = assess_dynamic_motion_eligibility(
        _envelope(),
        _candidate(),
        _dynamics(
            joint_accelerations_deg_s2={"base": 180.001, "shoulder": 0.0},
        ),
    )

    assert SafetyViolationCode.ACCELERATION_LIMIT_VIOLATION in _codes(result)


def test_static_rejection_short_circuits_dynamic_checks() -> None:
    candidate = MotionCandidate(
        system_state=SystemState.IDLE,
        estop_active=False,
        joint_targets_deg={"base": 0.0},
        workspace_point_mm=CartesianPoint(0.0, 0.0, 100.0),
    )

    result = assess_dynamic_motion_eligibility(_envelope(), candidate, _dynamics())

    assert result.decision is MotionDecision.REJECT
    assert _codes(result) == {SafetyViolationCode.STATE_NOT_ALLOWED}
