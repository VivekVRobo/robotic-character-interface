"""Cross-file fail-closed configuration validation."""

from rci.config.models import AppSettings, RobotWorkspaceSettings, ServoJointSettings
from rci.domain.enums import SystemState
from rci.domain.errors import ConfigurationError


def _validate_workspace(workspace: RobotWorkspaceSettings) -> None:
    pairs = (
        ("x", workspace.min_x_mm, workspace.max_x_mm),
        ("y", workspace.min_y_mm, workspace.max_y_mm),
        ("z", workspace.min_z_mm, workspace.max_z_mm),
    )
    for axis, minimum, maximum in pairs:
        if minimum is None or maximum is None:
            raise ConfigurationError(f"verified robot requires complete {axis}-workspace limits")
        if minimum >= maximum:
            raise ConfigurationError(f"workspace {axis} minimum must be less than maximum")


def _validate_verified_joint(name: str, joint: ServoJointSettings) -> None:
    values = (joint.min_deg, joint.neutral_deg, joint.max_deg)
    if any(value is None for value in values):
        raise ConfigurationError(f"verified servo joint {name!r} requires min/neutral/max angles")

    minimum = joint.min_deg
    neutral = joint.neutral_deg
    maximum = joint.max_deg
    assert minimum is not None and neutral is not None and maximum is not None
    if not minimum < neutral < maximum:
        raise ConfigurationError(f"servo joint {name!r} must satisfy min < neutral < max")


def validate_app_settings(settings: AppSettings) -> None:
    """Validate invariants that span individual Pydantic models/files."""
    if settings.system.startup_state is not SystemState.BOOT:
        raise ConfigurationError("startup_state must be BOOT")

    motion = settings.safety.motion
    if motion.heartbeat_timeout_ms <= motion.heartbeat_interval_ms:
        raise ConfigurationError("heartbeat timeout must exceed heartbeat interval")
    if motion.command_ttl_ms > motion.heartbeat_timeout_ms:
        raise ConfigurationError("command TTL must not exceed heartbeat timeout")

    if not settings.safety.estop.require_manual_reset:
        raise ConfigurationError("V1 safety requires explicit manual emergency-stop reset")

    allowed_motion_states = set(settings.safety.states.motion_allowed)
    permitted = {SystemState.ARMED, SystemState.EXECUTING}
    illegal = allowed_motion_states - permitted
    if illegal:
        names = ", ".join(sorted(state.value for state in illegal))
        raise ConfigurationError(f"motion cannot be enabled in states: {names}")

    if settings.servos.hardware_verified:
        if not settings.servos.joints:
            raise ConfigurationError("verified servo configuration requires joints")
        for name, joint in settings.servos.joints.items():
            _validate_verified_joint(name, joint)

    if settings.robot.hardware_verified:
        links = settings.robot.links
        if links.shoulder_mm is None or links.forearm_mm is None:
            raise ConfigurationError("verified robot requires measured link lengths")
        if not settings.robot.poses.home or not settings.robot.poses.safe:
            raise ConfigurationError("verified robot requires home and safe poses")
        _validate_workspace(settings.robot.workspace)

    if not settings.system.simulation:
        if not settings.robot.hardware_verified or not settings.servos.hardware_verified:
            raise ConfigurationError(
                "non-simulation mode requires verified robot and servo configurations"
            )
