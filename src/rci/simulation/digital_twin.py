"""Deterministic multi-joint digital twin for software-only robot validation."""

from __future__ import annotations

from dataclasses import dataclass
from math import copysign, sqrt

from rci.protocols.constants import WireSystemState
from rci.protocols.messages import RobotJointTelemetry, RobotTelemetry, ValidatedMotionCommand
from rci.robotics.model import RobotModel, RobotModelError


class DigitalTwinError(ValueError):
    """Raised when a wire command cannot be represented by the reference robot model."""


@dataclass(frozen=True, slots=True)
class DigitalTwinState:
    uptime_ms: int
    state: WireSystemState
    positions_deg: dict[str, float]
    velocities_deg_s: dict[str, float]
    targets_deg: dict[str, float]
    currents_ma: dict[str, int]
    supply_mv: int


class DigitalTwinRobot:
    """Acceleration-limited servo-like plant driven only by validated semantic commands."""

    def __init__(self, model: RobotModel, *, supply_mv: int = 6000) -> None:
        if not 1 <= supply_mv <= 65535:
            raise DigitalTwinError("simulated supply voltage must fit uint16 millivolts")
        self.model = model
        self.supply_mv = supply_mv
        self._positions = model.home
        self._velocities = {name: 0.0 for name in model.joint_names}
        self._targets = dict(self._positions)
        self._currents = {name: 80 for name in model.joint_names}
        self._uptime_ms = 0
        self._state = WireSystemState.IDLE
        self._command_velocity_limit = min(
            joint.max_velocity_deg_s for joint in model.profile.joints.values()
        )
        self._command_acceleration_limit = min(
            joint.max_acceleration_deg_s2 for joint in model.profile.joints.values()
        )
        self._id_to_name = {joint.protocol_id: name for name, joint in model.profile.joints.items()}

    @property
    def state(self) -> DigitalTwinState:
        return DigitalTwinState(
            uptime_ms=self._uptime_ms,
            state=self._state,
            positions_deg=dict(self._positions),
            velocities_deg_s=dict(self._velocities),
            targets_deg=dict(self._targets),
            currents_ma=dict(self._currents),
            supply_mv=self.supply_mv,
        )

    def accept(self, command: ValidatedMotionCommand) -> None:
        targets = dict(self._targets)
        for target in command.targets:
            name = self._id_to_name.get(target.joint_id)
            if name is None:
                raise DigitalTwinError(f"unknown simulated joint id {target.joint_id}")
            targets[name] = target.target_cdeg / 100.0
        try:
            self.model.validate_joint_positions(targets)
        except RobotModelError as exc:
            raise DigitalTwinError(f"simulated command violates reference model: {exc}") from exc

        self._targets = targets
        self._command_velocity_limit = command.max_velocity_cdeg_s / 100.0
        self._command_acceleration_limit = command.max_acceleration_cdeg_s2 / 100.0
        self._state = WireSystemState.EXECUTING

    def estop(self) -> None:
        self._targets = dict(self._positions)
        self._velocities = {name: 0.0 for name in self.model.joint_names}
        self._state = WireSystemState.ESTOP

    def reset_estop(self) -> None:
        if self._state is WireSystemState.ESTOP:
            self._state = WireSystemState.IDLE

    def step(self, dt_s: float) -> DigitalTwinState:
        if dt_s <= 0:
            raise DigitalTwinError("digital twin step must be positive")
        self._uptime_ms = min(0xFFFFFFFF, self._uptime_ms + round(dt_s * 1000.0))
        if self._state is WireSystemState.ESTOP:
            self._currents = {name: 60 for name in self.model.joint_names}
            return self.state

        moving = False
        for name in self.model.joint_names:
            spec = self.model.profile.joints[name]
            position = self._positions[name]
            velocity = self._velocities[name]
            error = self._targets[name] - position
            velocity_limit = min(spec.max_velocity_deg_s, self._command_velocity_limit)
            acceleration_limit = min(
                spec.max_acceleration_deg_s2,
                self._command_acceleration_limit,
            )

            if abs(error) <= 1e-6 and abs(velocity) <= 1e-6:
                self._positions[name] = self._targets[name]
                self._velocities[name] = 0.0
                self._currents[name] = 80
                continue

            moving = True
            braking_velocity = sqrt(max(0.0, 2.0 * acceleration_limit * abs(error)))
            desired_velocity = copysign(min(velocity_limit, braking_velocity), error)
            max_delta_velocity = acceleration_limit * dt_s
            delta_velocity = desired_velocity - velocity
            if abs(delta_velocity) > max_delta_velocity:
                velocity += copysign(max_delta_velocity, delta_velocity)
            else:
                velocity = desired_velocity

            next_position = position + velocity * dt_s
            if (self._targets[name] - position) * (self._targets[name] - next_position) <= 0:
                next_position = self._targets[name]
                velocity = 0.0

            self._positions[name] = next_position
            self._velocities[name] = velocity
            simulated_current = 80.0 + 3.0 * abs(velocity) + 0.6 * abs(error)
            self._currents[name] = min(1200, round(simulated_current))

        self._state = WireSystemState.EXECUTING if moving else WireSystemState.IDLE
        return self.state

    def telemetry(self, *, flags: int = 0) -> RobotTelemetry:
        joints = tuple(
            RobotJointTelemetry(
                joint_id=self.model.profile.joints[name].protocol_id,
                position_cdeg=round(self._positions[name] * 100.0),
                velocity_cdeg_s=round(self._velocities[name] * 100.0),
                current_ma=self._currents[name],
            )
            for name in self.model.joint_names
        )
        return RobotTelemetry(
            uptime_ms=self._uptime_ms,
            state=self._state,
            flags=flags,
            supply_mv=self.supply_mv,
            joints=joints,
        )
