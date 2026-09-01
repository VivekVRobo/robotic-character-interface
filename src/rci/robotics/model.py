"""Deterministic simulation robot model built from an explicit reference profile."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from rci.robotics.models import ReferenceRobotProfile, WorkspaceEstimate


class RobotModelError(ValueError):
    """Raised when a joint vector violates the reference model."""


@dataclass(frozen=True, slots=True)
class RobotModel:
    profile: ReferenceRobotProfile

    @property
    def joint_names(self) -> tuple[str, ...]:
        return tuple(self.profile.joints)

    @property
    def home(self) -> dict[str, float]:
        return {name: spec.home_deg for name, spec in self.profile.joints.items()}

    @property
    def arm_reach_mm(self) -> float:
        geometry = self.profile.geometry
        return geometry.shoulder_link_mm + geometry.forearm_link_mm + geometry.tool_length_mm

    def validate_joint_positions(self, joints_deg: dict[str, float]) -> None:
        if set(joints_deg) != set(self.profile.joints):
            raise RobotModelError("joint vector must contain exactly the reference robot joints")
        for name, value in joints_deg.items():
            if not isfinite(value):
                raise RobotModelError(f"joint {name} is not finite")
            spec = self.profile.joints[name]
            if not spec.lower_deg <= value <= spec.upper_deg:
                raise RobotModelError(
                    f"joint {name} target {value} is outside "
                    f"[{spec.lower_deg}, {spec.upper_deg}]"
                )

    def within_limits(self, joints_deg: dict[str, float]) -> bool:
        try:
            self.validate_joint_positions(joints_deg)
        except RobotModelError:
            return False
        return True

    def workspace_estimate_from_points(
        self,
        points: tuple[tuple[float, float, float], ...],
    ) -> WorkspaceEstimate:
        if not points:
            raise RobotModelError("workspace estimate requires at least one point")
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        zs = [point[2] for point in points]
        return WorkspaceEstimate(
            min_x_mm=min(xs),
            max_x_mm=max(xs),
            min_y_mm=min(ys),
            max_y_mm=max(ys),
            min_z_mm=min(zs),
            max_z_mm=max(zs),
            samples=len(points),
        )
