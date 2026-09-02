"""Reference-model controller that produces safety-compatible motion candidates."""

from __future__ import annotations

from dataclasses import dataclass

from rci.domain.enums import SystemState
from rci.robotics.kinematics import Kinematics
from rci.robotics.model import RobotModel
from rci.robotics.models import CartesianPose, JointTrajectory
from rci.robotics.trajectory import TrajectoryGenerator
from rci.safety.models import CartesianPoint, MotionCandidate, MotionDynamics


@dataclass(frozen=True, slots=True)
class PlannedMotion:
    target_pose: CartesianPose
    target_joints_deg: dict[str, float]
    trajectory: JointTrajectory

    def terminal_safety_inputs(
        self,
        *,
        system_state: SystemState,
        estop_active: bool,
        command_age_ms: float,
        heartbeat_age_ms: float,
    ) -> tuple[MotionCandidate, MotionDynamics]:
        terminal = self.trajectory.end
        candidate = MotionCandidate(
            system_state=system_state,
            estop_active=estop_active,
            joint_targets_deg=self.target_joints_deg,
            workspace_point_mm=CartesianPoint(
                x_mm=self.target_pose.x_mm,
                y_mm=self.target_pose.y_mm,
                z_mm=self.target_pose.z_mm,
            ),
        )
        dynamics = MotionDynamics(
            command_age_ms=command_age_ms,
            heartbeat_age_ms=heartbeat_age_ms,
            joint_velocities_deg_s=terminal.velocities_deg_s,
            joint_accelerations_deg_s2=terminal.accelerations_deg_s2,
        )
        return candidate, dynamics


class RobotController:
    """Planning facade for the simulation/reference robot model."""

    def __init__(self, model: RobotModel) -> None:
        self.model = model
        self.kinematics = Kinematics(model)
        self.trajectory = TrajectoryGenerator(model)

    def plan_cartesian(
        self,
        *,
        current_joints_deg: dict[str, float],
        target_pose: CartesianPose,
        gripper_deg: float | None = None,
        sample_period_s: float = 0.02,
    ) -> PlannedMotion:
        self.model.validate_joint_positions(current_joints_deg)
        solution = self.kinematics.inverse(
            target_pose,
            gripper_deg=gripper_deg,
            seed_deg=current_joints_deg,
        )
        return self.plan_joint_targets(
            current_joints_deg=current_joints_deg,
            target_joints_deg=solution.as_dict(),
            sample_period_s=sample_period_s,
        )

    def plan_joint_targets(
        self,
        *,
        current_joints_deg: dict[str, float],
        target_joints_deg: dict[str, float],
        sample_period_s: float = 0.02,
    ) -> PlannedMotion:
        """Plan an exact bounded joint goal and derive its Cartesian terminal pose."""
        self.model.validate_joint_positions(current_joints_deg)
        self.model.validate_joint_positions(target_joints_deg)
        trajectory = self.trajectory.generate(
            current_joints_deg,
            target_joints_deg,
            sample_period_s=sample_period_s,
        )
        return PlannedMotion(
            target_pose=self.kinematics.forward(target_joints_deg),
            target_joints_deg=dict(target_joints_deg),
            trajectory=trajectory,
        )
