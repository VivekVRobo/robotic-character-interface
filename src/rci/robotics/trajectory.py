"""Deterministic cubic time-scaling trajectory generation."""

from __future__ import annotations

from math import ceil, sqrt

from rci.robotics.model import RobotModel
from rci.robotics.models import JointTrajectory, TrajectorySample


class TrajectoryError(ValueError):
    """Raised when a requested reference-model trajectory is invalid."""


class TrajectoryGenerator:
    def __init__(self, model: RobotModel) -> None:
        self.model = model

    def minimum_duration(self, start_deg: dict[str, float], target_deg: dict[str, float]) -> float:
        """Return a duration safe under the scalar v1 dynamic policy.

        MotionSafetyPolicy currently exposes one global velocity and acceleration
        limit, so trajectories use the strictest predicted joint limits for every
        joint. This is intentionally conservative and keeps planning aligned with
        the safety supervisor instead of weakening the supervisor for simulation.
        """
        self.model.validate_joint_positions(start_deg)
        self.model.validate_joint_positions(target_deg)
        global_velocity_limit = min(
            joint.max_velocity_deg_s for joint in self.model.profile.joints.values()
        )
        global_acceleration_limit = min(
            joint.max_acceleration_deg_s2 for joint in self.model.profile.joints.values()
        )
        duration = 0.0
        for name, start in start_deg.items():
            delta = abs(target_deg[name] - start)
            if delta == 0:
                continue
            velocity_bound = 1.5 * delta / global_velocity_limit
            acceleration_bound = sqrt(6.0 * delta / global_acceleration_limit)
            duration = max(duration, velocity_bound, acceleration_bound)
        return max(duration, 0.05)

    def generate(
        self,
        start_deg: dict[str, float],
        target_deg: dict[str, float],
        *,
        sample_period_s: float = 0.02,
        duration_s: float | None = None,
    ) -> JointTrajectory:
        if sample_period_s <= 0:
            raise TrajectoryError("sample period must be positive")
        minimum = self.minimum_duration(start_deg, target_deg)
        duration = minimum if duration_s is None else duration_s
        if duration + 1e-12 < minimum:
            raise TrajectoryError(
                f"requested duration {duration:.6f}s is below bounded minimum {minimum:.6f}s"
            )

        steps = max(1, ceil(duration / sample_period_s))
        samples: list[TrajectorySample] = []
        for index in range(steps + 1):
            time_s = duration * index / steps
            u = 0.0 if duration == 0 else time_s / duration
            scale = 3.0 * u * u - 2.0 * u * u * u
            scale_velocity = (6.0 * u - 6.0 * u * u) / duration
            scale_acceleration = (6.0 - 12.0 * u) / (duration * duration)

            positions: dict[str, float] = {}
            velocities: dict[str, float] = {}
            accelerations: dict[str, float] = {}
            for name, start in start_deg.items():
                delta = target_deg[name] - start
                positions[name] = start + delta * scale
                velocities[name] = delta * scale_velocity
                accelerations[name] = delta * scale_acceleration

            samples.append(
                TrajectorySample(
                    time_s=time_s,
                    positions_deg=positions,
                    velocities_deg_s=velocities,
                    accelerations_deg_s2=accelerations,
                )
            )

        return JointTrajectory(duration_s=duration, samples=tuple(samples))
