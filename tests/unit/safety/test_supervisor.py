from pathlib import Path

import pytest

from rci.config.loader import ConfigLoader
from rci.domain.enums import MotionDecision, SystemState
from rci.safety.lifecycle import SafetyLifecycleController, SafetyLifecyclePolicy, SafetyStopCause
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
from rci.safety.supervisor import MotionSafetySupervisor


def _verified_envelope() -> SafetyEnvelope:
    return SafetyEnvelope(
        joints={
            "base": JointConstraint("base", -90.0, 90.0, 0.0, True),
            "shoulder": JointConstraint("shoulder", -45.0, 120.0, 20.0, True),
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
        motion_policy=MotionSafetyPolicy(
            command_ttl_ms=250.0,
            heartbeat_timeout_ms=500.0,
            max_velocity_deg_s=60.0,
            max_acceleration_deg_s2=180.0,
        ),
    )


def _candidate(**overrides: object) -> MotionCandidate:
    values: dict[str, object] = {
        "system_state": SystemState.ARMED,
        "estop_active": False,
        "joint_targets_deg": {"base": 10.0, "shoulder": 30.0},
        "workspace_point_mm": CartesianPoint(100.0, 0.0, 200.0),
    }
    values.update(overrides)
    return MotionCandidate(**values)  # type: ignore[arg-type]


def _dynamics(**overrides: object) -> MotionDynamics:
    values: dict[str, object] = {
        "command_age_ms": 10.0,
        "heartbeat_age_ms": 10.0,
        "joint_velocities_deg_s": {"base": 20.0, "shoulder": 20.0},
        "joint_accelerations_deg_s2": {"base": 40.0, "shoulder": 40.0},
    }
    values.update(overrides)
    return MotionDynamics(**values)  # type: ignore[arg-type]


def _supervisor() -> MotionSafetySupervisor:
    lifecycle = SafetyLifecycleController(
        SafetyLifecyclePolicy(heartbeat_timeout_ms=500.0, require_manual_reset=True)
    )
    return MotionSafetySupervisor(_verified_envelope(), lifecycle)


def _healthy_supervisor() -> MotionSafetySupervisor:
    supervisor = _supervisor()
    supervisor.arm_watchdog()
    supervisor.observe_heartbeat_age(0.0)
    return supervisor


def test_watchdog_must_be_armed_before_authorization() -> None:
    result = _supervisor().evaluate(_candidate(), _dynamics())

    assert result.decision is MotionDecision.REJECT
    assert result.authorization is None
    assert [violation.code for violation in result.violations] == [
        SafetyViolationCode.WATCHDOG_NOT_ARMED
    ]


def test_complete_safety_stack_mints_immutable_authorization() -> None:
    supervisor = _healthy_supervisor()

    result = supervisor.evaluate(_candidate(), _dynamics())

    assert result.approved
    assert result.authorization is not None
    authorization = result.authorization
    assert authorization.joint_targets_deg == {"base": 10.0, "shoulder": 30.0}
    assert authorization.command_ttl_ms == 250.0
    assert authorization.max_velocity_deg_s == 60.0
    assert authorization.max_acceleration_deg_s2 == 180.0
    assert authorization.lifecycle_sequence == result.lifecycle.sequence
    with pytest.raises(TypeError):
        authorization.joint_targets_deg["base"] = 20.0  # type: ignore[index]


def test_static_safety_failure_never_mints_authorization() -> None:
    supervisor = _healthy_supervisor()

    result = supervisor.evaluate(
        _candidate(joint_targets_deg={"base": 91.0, "shoulder": 30.0}),
        _dynamics(),
    )

    assert result.decision is MotionDecision.REJECT
    assert result.authorization is None
    assert SafetyViolationCode.JOINT_LIMIT_VIOLATION in {
        violation.code for violation in result.violations
    }


def test_dynamic_safety_failure_never_mints_authorization() -> None:
    supervisor = _healthy_supervisor()

    result = supervisor.evaluate(
        _candidate(),
        _dynamics(command_age_ms=251.0),
    )

    assert result.decision is MotionDecision.REJECT
    assert result.authorization is None
    assert SafetyViolationCode.COMMAND_STALE in {violation.code for violation in result.violations}


def test_watchdog_timeout_is_escalated_to_estop() -> None:
    supervisor = _healthy_supervisor()

    result = supervisor.evaluate(
        _candidate(),
        _dynamics(heartbeat_age_ms=501.0),
    )

    assert result.decision is MotionDecision.ESTOP
    assert result.authorization is None
    assert result.lifecycle.estop_latched
    assert SafetyStopCause.WATCHDOG_TIMEOUT in result.lifecycle.causes
    assert result.violations[0].code is SafetyViolationCode.LIFECYCLE_ESTOP_LATCHED


def test_software_estop_has_priority_over_valid_motion() -> None:
    supervisor = _healthy_supervisor()
    supervisor.trigger_software_estop("operator stop")

    result = supervisor.evaluate(_candidate(), _dynamics())

    assert result.decision is MotionDecision.ESTOP
    assert result.authorization is None
    assert result.violations[0].code is SafetyViolationCode.LIFECYCLE_ESTOP_LATCHED


def test_physical_estop_has_priority_and_remains_latched_after_release() -> None:
    supervisor = _healthy_supervisor()

    pressed = supervisor.evaluate(_candidate(estop_active=True), _dynamics())
    assert pressed.decision is MotionDecision.ESTOP

    released = supervisor.evaluate(_candidate(estop_active=False), _dynamics())
    assert released.decision is MotionDecision.ESTOP
    assert released.lifecycle.estop_latched

    reset = supervisor.request_manual_reset()
    assert reset.cleared

    recovered = supervisor.evaluate(_candidate(), _dynamics())
    assert recovered.approved


def test_canonical_unverified_configuration_cannot_mint_authorization() -> None:
    settings = ConfigLoader(Path("configs")).load()
    supervisor = MotionSafetySupervisor.from_settings(settings)
    supervisor.arm_watchdog()
    supervisor.observe_heartbeat_age(0.0)

    result = supervisor.evaluate(_candidate(), _dynamics())

    assert result.decision is MotionDecision.REJECT
    assert result.authorization is None
    assert SafetyViolationCode.JOINT_MODEL_UNVERIFIED in {
        violation.code for violation in result.violations
    }


def test_lifecycle_and_dynamic_heartbeat_policies_must_match() -> None:
    lifecycle = SafetyLifecycleController(
        SafetyLifecyclePolicy(heartbeat_timeout_ms=400.0, require_manual_reset=True)
    )

    with pytest.raises(ValueError, match="heartbeat timeouts must match"):
        MotionSafetySupervisor(_verified_envelope(), lifecycle)
