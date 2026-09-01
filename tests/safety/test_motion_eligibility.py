from rci.config.loader import ConfigLoader
from rci.domain.enums import MotionDecision, SystemState
from rci.safety.eligibility import assess_motion_eligibility
from rci.safety.factory import build_safety_envelope
from rci.safety.models import CartesianPoint, MotionCandidate, SafetyViolationCode


def test_canonical_unverified_hardware_configuration_fails_closed() -> None:
    settings = ConfigLoader().load()
    envelope = build_safety_envelope(settings)

    assert not envelope.physical_constraints_verified

    candidate = MotionCandidate(
        system_state=SystemState.ARMED,
        estop_active=False,
        joint_targets_deg={"base": 0.0},
        workspace_point_mm=CartesianPoint(0.0, 0.0, 0.0),
    )
    result = assess_motion_eligibility(envelope, candidate)
    codes = {violation.code for violation in result.violations}

    assert result.decision is MotionDecision.REJECT
    assert SafetyViolationCode.JOINT_MODEL_UNVERIFIED in codes
    assert SafetyViolationCode.WORKSPACE_MODEL_UNVERIFIED in codes


def test_numeric_placeholders_cannot_override_unverified_flags() -> None:
    settings = ConfigLoader().load()
    for joint in settings.servos.joints.values():
        joint.min_deg = -180.0
        joint.neutral_deg = 0.0
        joint.max_deg = 180.0

    workspace = settings.robot.workspace
    workspace.min_x_mm = -1000.0
    workspace.max_x_mm = 1000.0
    workspace.min_y_mm = -1000.0
    workspace.max_y_mm = 1000.0
    workspace.min_z_mm = -1000.0
    workspace.max_z_mm = 1000.0

    envelope = build_safety_envelope(settings)

    assert not settings.servos.hardware_verified
    assert not settings.robot.hardware_verified
    assert not envelope.physical_constraints_verified
