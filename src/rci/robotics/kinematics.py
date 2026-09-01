"""Forward/inverse kinematics for the reference 3-axis arm plus gripper."""

from __future__ import annotations

from math import acos, atan2, cos, degrees, hypot, radians, sin

from rci.robotics.model import RobotModel, RobotModelError
from rci.robotics.models import CartesianPose, JointSolution, WorkspaceEstimate


class KinematicsError(ValueError):
    """Raised when a Cartesian target has no valid reference-model solution."""


class Kinematics:
    def __init__(self, model: RobotModel) -> None:
        self.model = model

    def forward(self, joints_deg: dict[str, float]) -> CartesianPose:
        self.model.validate_joint_positions(joints_deg)
        geometry = self.model.profile.geometry
        base = radians(joints_deg["base"])
        shoulder = radians(joints_deg["shoulder"])
        elbow = radians(joints_deg["elbow"])
        distal = geometry.forearm_link_mm + geometry.tool_length_mm

        radial = geometry.shoulder_link_mm * cos(shoulder) + distal * cos(shoulder + elbow)
        z_mm = (
            geometry.base_height_mm
            + geometry.shoulder_link_mm * sin(shoulder)
            + distal * sin(shoulder + elbow)
        )
        return CartesianPose(
            x_mm=radial * cos(base),
            y_mm=radial * sin(base),
            z_mm=z_mm,
        )

    def inverse(
        self,
        target: CartesianPose,
        *,
        gripper_deg: float | None = None,
        seed_deg: dict[str, float] | None = None,
    ) -> JointSolution:
        geometry = self.model.profile.geometry
        distal = geometry.forearm_link_mm + geometry.tool_length_mm
        radial = hypot(target.x_mm, target.y_mm)
        vertical = target.z_mm - geometry.base_height_mm
        base_deg = degrees(atan2(target.y_mm, target.x_mm))

        numerator = radial * radial + vertical * vertical - geometry.shoulder_link_mm**2 - distal**2
        denominator = 2.0 * geometry.shoulder_link_mm * distal
        cosine_elbow = numerator / denominator
        if cosine_elbow < -1.0 - 1e-9 or cosine_elbow > 1.0 + 1e-9:
            raise KinematicsError("target is outside the reference arm reach")
        cosine_elbow = min(1.0, max(-1.0, cosine_elbow))

        elbow_magnitude = acos(cosine_elbow)
        candidates: list[JointSolution] = []
        requested_gripper = (
            self.model.profile.joints["gripper"].home_deg if gripper_deg is None else gripper_deg
        )
        for elbow in (elbow_magnitude, -elbow_magnitude):
            shoulder = atan2(vertical, radial) - atan2(
                distal * sin(elbow),
                geometry.shoulder_link_mm + distal * cos(elbow),
            )
            solution = JointSolution(
                base_deg=base_deg,
                shoulder_deg=degrees(shoulder),
                elbow_deg=degrees(elbow),
                gripper_deg=requested_gripper,
            )
            if self.model.within_limits(solution.as_dict()):
                candidates.append(solution)

        if not candidates:
            raise KinematicsError("target has no solution within reference joint limits")
        if seed_deg is None:
            return min(candidates, key=lambda item: abs(item.elbow_deg))

        try:
            self.model.validate_joint_positions(seed_deg)
        except RobotModelError as exc:
            raise KinematicsError(f"invalid inverse-kinematics seed: {exc}") from exc

        def distance(solution: JointSolution) -> float:
            values = solution.as_dict()
            return sum((values[name] - seed_deg[name]) ** 2 for name in values)

        return min(candidates, key=distance)

    def estimate_workspace(self, *, samples_per_joint: int = 9) -> WorkspaceEstimate:
        if samples_per_joint < 2:
            raise KinematicsError("workspace sampling requires at least two samples per arm joint")

        def axis_samples(name: str) -> tuple[float, ...]:
            spec = self.model.profile.joints[name]
            span = spec.upper_deg - spec.lower_deg
            return tuple(
                spec.lower_deg + span * index / (samples_per_joint - 1)
                for index in range(samples_per_joint)
            )

        points: list[tuple[float, float, float]] = []
        gripper_home = self.model.profile.joints["gripper"].home_deg
        for base in axis_samples("base"):
            for shoulder in axis_samples("shoulder"):
                for elbow in axis_samples("elbow"):
                    pose = self.forward(
                        {
                            "base": base,
                            "shoulder": shoulder,
                            "elbow": elbow,
                            "gripper": gripper_home,
                        }
                    )
                    points.append((pose.x_mm, pose.y_mm, pose.z_mm))
        return self.model.workspace_estimate_from_points(tuple(points))
