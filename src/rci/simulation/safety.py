"""Synthetic verified safety envelope used only by the digital-twin runtime."""

from __future__ import annotations

from rci.domain.enums import SystemState
from rci.robotics.kinematics import Kinematics
from rci.robotics.model import RobotModel
from rci.safety.lifecycle import SafetyLifecycleController, SafetyLifecyclePolicy
from rci.safety.models import (
    JointConstraint,
    MotionSafetyPolicy,
    SafetyEnvelope,
    WorkspaceBounds,
)
from rci.safety.supervisor import MotionSafetySupervisor


def build_simulation_supervisor(model: RobotModel) -> MotionSafetySupervisor:
    """Build an explicitly synthetic safety context; never represents physical verification."""
    if not model.profile.simulation_only or model.profile.hardware_verified:
        raise ValueError("simulation supervisor requires an unverified simulation-only profile")

    workspace = Kinematics(model).estimate_workspace(samples_per_joint=5)
    envelope = SafetyEnvelope(
        joints={
            name: JointConstraint(
                name=name,
                min_deg=joint.lower_deg,
                max_deg=joint.upper_deg,
                neutral_deg=joint.home_deg,
                verified=True,
            )
            for name, joint in model.profile.joints.items()
        },
        workspace=WorkspaceBounds(
            min_x_mm=workspace.min_x_mm,
            max_x_mm=workspace.max_x_mm,
            min_y_mm=workspace.min_y_mm,
            max_y_mm=workspace.max_y_mm,
            min_z_mm=workspace.min_z_mm,
            max_z_mm=workspace.max_z_mm,
            verified=True,
        ),
        allowed_states=frozenset({SystemState.ARMED}),
        robot_verified=True,
        servos_verified=True,
        motion_policy=MotionSafetyPolicy(
            command_ttl_ms=250.0,
            heartbeat_timeout_ms=500.0,
            max_velocity_deg_s=min(
                joint.max_velocity_deg_s for joint in model.profile.joints.values()
            ),
            max_acceleration_deg_s2=min(
                joint.max_acceleration_deg_s2 for joint in model.profile.joints.values()
            ),
        ),
    )
    lifecycle = SafetyLifecycleController(SafetyLifecyclePolicy(heartbeat_timeout_ms=500.0))
    supervisor = MotionSafetySupervisor(envelope, lifecycle)
    supervisor.arm_watchdog()
    return supervisor
