"""Build deterministic safety envelopes from validated application settings."""

from __future__ import annotations

from rci.config.models import AppSettings
from rci.safety.models import JointConstraint, SafetyEnvelope, WorkspaceBounds


def build_safety_envelope(settings: AppSettings) -> SafetyEnvelope:
    """Translate configuration into a fail-closed physical safety envelope."""
    joints = {
        name: JointConstraint(
            name=name,
            min_deg=joint.min_deg,
            max_deg=joint.max_deg,
            neutral_deg=joint.neutral_deg,
            verified=(
                settings.servos.hardware_verified
                and joint.min_deg is not None
                and joint.max_deg is not None
                and joint.neutral_deg is not None
            ),
        )
        for name, joint in settings.servos.joints.items()
    }

    workspace_config = settings.robot.workspace
    workspace_complete = all(
        value is not None
        for value in (
            workspace_config.min_x_mm,
            workspace_config.max_x_mm,
            workspace_config.min_y_mm,
            workspace_config.max_y_mm,
            workspace_config.min_z_mm,
            workspace_config.max_z_mm,
        )
    )
    workspace = WorkspaceBounds(
        min_x_mm=workspace_config.min_x_mm,
        max_x_mm=workspace_config.max_x_mm,
        min_y_mm=workspace_config.min_y_mm,
        max_y_mm=workspace_config.max_y_mm,
        min_z_mm=workspace_config.min_z_mm,
        max_z_mm=workspace_config.max_z_mm,
        verified=settings.robot.hardware_verified and workspace_complete,
    )

    return SafetyEnvelope(
        joints=joints,
        workspace=workspace,
        allowed_states=frozenset(settings.safety.states.motion_allowed),
        robot_verified=settings.robot.hardware_verified,
        servos_verified=settings.servos.hardware_verified,
    )
