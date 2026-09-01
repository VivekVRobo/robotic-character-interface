from math import nan

from rci.domain.enums import MotionDecision, SystemState
from rci.safety.eligibility import assess_motion_eligibility
from rci.safety.models import (
    CartesianPoint,
    JointConstraint,
    MotionCandidate,
    SafetyEnvelope,
    SafetyViolationCode,
    WorkspaceBounds,
)


def _verified_envelope() -> SafetyEnvelope:
    return SafetyEnvelope(
        joints={
            "base": JointConstraint(
                name="base",
                min_deg=-90.0,
                max_deg=90.0,
                neutral_deg=0.0,
                verified=True,
            ),
            "shoulder": JointConstraint(
                name="shoulder",
                min_deg=-45.0,
                max_deg=120.0,
                neutral_deg=20.0,
                verified=True,
            ),
        },
        workspace=WorkspaceBounds(
            min_x_mm=-300.0,
            max_x_mm=300.0,
            min_y_mm=-300.0,
            max_y_mm=300.0,
            min_z_mm=0.0,
            max_z_mm=500.0,
            verified=True,
        ),
        allowed_states=frozenset({SystemState.ARMED, SystemState.EXECUTING}),
        robot_verified=True,
        servos_verified=True,
    )


def _candidate(**overrides: object) -> MotionCandidate:
    values: dict[str, object] = {
        "system_state": SystemState.ARMED,
        "estop_active": False,
        "joint_targets_deg": {"base": 0.0, "shoulder": 20.0},
        "workspace_point_mm": CartesianPoint(100.0, 0.0, 200.0),
    }
    values.update(overrides)
    return MotionCandidate(**values)  # type: ignore[arg-type]


def _codes(result: object) -> set[SafetyViolationCode]:
    return {violation.code for violation in result.violations}  # type: ignore[attr-defined]


def test_verified_candidate_is_approved() -> None:
    result = assess_motion_eligibility(_verified_envelope(), _candidate())

    assert result.decision is MotionDecision.APPROVE
    assert result.approved
    assert result.violations == ()


def test_joint_and_workspace_boundaries_are_inclusive() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(
            joint_targets_deg={"base": -90.0, "shoulder": 120.0},
            workspace_point_mm=CartesianPoint(300.0, -300.0, 500.0),
        ),
    )

    assert result.approved


def test_joint_limit_violation_rejects_candidate() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(joint_targets_deg={"base": 91.0, "shoulder": 20.0}),
    )

    assert result.decision is MotionDecision.REJECT
    assert SafetyViolationCode.JOINT_LIMIT_VIOLATION in _codes(result)


def test_unknown_joint_rejects_candidate() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(joint_targets_deg={"wrist": 0.0}),
    )

    assert SafetyViolationCode.UNKNOWN_JOINT in _codes(result)


def test_workspace_limit_violation_rejects_candidate() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(workspace_point_mm=CartesianPoint(301.0, 0.0, 200.0)),
    )

    assert SafetyViolationCode.WORKSPACE_LIMIT_VIOLATION in _codes(result)


def test_workspace_point_is_required_for_physical_eligibility() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(workspace_point_mm=None),
    )

    assert SafetyViolationCode.WORKSPACE_TARGET_REQUIRED in _codes(result)


def test_nonfinite_target_rejects_candidate() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(joint_targets_deg={"base": nan}),
    )

    assert SafetyViolationCode.INVALID_NUMERIC_TARGET in _codes(result)


def test_illegal_state_rejects_motion() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(system_state=SystemState.IDLE),
    )

    assert SafetyViolationCode.STATE_NOT_ALLOWED in _codes(result)


def test_estop_has_priority_over_other_eligibility_checks() -> None:
    result = assess_motion_eligibility(
        _verified_envelope(),
        _candidate(system_state=SystemState.IDLE, estop_active=True),
    )

    assert result.decision is MotionDecision.ESTOP
    assert [violation.code for violation in result.violations] == [
        SafetyViolationCode.ESTOP_ACTIVE
    ]
