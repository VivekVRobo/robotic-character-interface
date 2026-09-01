from rci.config.loader import ConfigLoader
from rci.domain.enums import MotionDecision, SystemState
from rci.safety.dynamics import assess_dynamic_motion_eligibility
from rci.safety.factory import build_safety_envelope
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


def _verified_envelope() -> SafetyEnvelope:
    return SafetyEnvelope(
        joints={"base": JointConstraint("base", -90.0, 90.0, 0.0, True)},
        workspace=WorkspaceBounds(-250.0, 250.0, -250.0, 250.0, 0.0, 400.0, True),
        allowed_states=frozenset({SystemState.ARMED, SystemState.EXECUTING}),
        robot_verified=True,
        servos_verified=True,
        motion_policy=MotionSafetyPolicy(250.0, 500.0, 60.0, 180.0),
    )


def _candidate() -> MotionCandidate:
    return MotionCandidate(
        system_state=SystemState.ARMED,
        estop_active=False,
        joint_targets_deg={"base": 0.0},
        workspace_point_mm=CartesianPoint(0.0, 0.0, 100.0),
    )


def test_canonical_dynamic_policy_is_derived_from_safety_config() -> None:
    envelope = build_safety_envelope(ConfigLoader().load())

    assert envelope.motion_policy is not None
    assert envelope.motion_policy.command_ttl_ms == 250.0
    assert envelope.motion_policy.heartbeat_timeout_ms == 500.0
    assert envelope.motion_policy.max_velocity_deg_s == 60.0
    assert envelope.motion_policy.max_acceleration_deg_s2 == 180.0


def test_stale_command_and_heartbeat_fail_closed() -> None:
    dynamics = MotionDynamics(
        command_age_ms=251.0,
        heartbeat_age_ms=501.0,
        joint_velocities_deg_s={"base": 0.0},
        joint_accelerations_deg_s2={"base": 0.0},
    )

    result = assess_dynamic_motion_eligibility(_verified_envelope(), _candidate(), dynamics)
    codes = {violation.code for violation in result.violations}

    assert result.decision is MotionDecision.REJECT
    assert SafetyViolationCode.COMMAND_STALE in codes
    assert SafetyViolationCode.HEARTBEAT_STALE in codes


def test_rate_limit_violation_cannot_be_clamped_into_approval() -> None:
    dynamics = MotionDynamics(
        command_age_ms=1.0,
        heartbeat_age_ms=1.0,
        joint_velocities_deg_s={"base": 61.0},
        joint_accelerations_deg_s2={"base": 181.0},
    )

    result = assess_dynamic_motion_eligibility(_verified_envelope(), _candidate(), dynamics)
    codes = {violation.code for violation in result.violations}

    assert result.decision is MotionDecision.REJECT
    assert SafetyViolationCode.VELOCITY_LIMIT_VIOLATION in codes
    assert SafetyViolationCode.ACCELERATION_LIMIT_VIOLATION in codes
