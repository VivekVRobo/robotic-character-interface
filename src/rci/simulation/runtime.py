"""End-to-end software runtime from semantic behavior to digital-twin telemetry."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from uuid import UUID

from rci.behavior.embodiment import SimulationBehaviorEmbodimentPlanner
from rci.behavior.planner import BehaviorIntent
from rci.domain.enums import MotionDecision, SystemState
from rci.hardware.robot_gateway import GatewayReceipt, RobotGateway
from rci.protocols.constants import AckStatus, EstopReason, WireSystemState
from rci.protocols.messages import RobotTelemetry
from rci.robotics.controller import RobotController
from rci.robotics.model import RobotModel
from rci.simulation.device import DigitalTwinProtocolDevice
from rci.simulation.digital_twin import DigitalTwinRobot
from rci.simulation.protocol_link import SimulatedProtocolLink
from rci.simulation.safety import build_simulation_supervisor


class SimulationRuntimeError(RuntimeError):
    """Raised when a software-only behavior execution cannot complete safely."""


@dataclass(frozen=True, slots=True)
class SimulationExecutionReport:
    cue: str
    style: str
    safety_decision: MotionDecision
    authorization_id: UUID
    heartbeat_ack: AckStatus
    motion_ack: AckStatus
    simulation_steps: int
    simulated_duration_s: float
    telemetry: RobotTelemetry
    simulation_only: bool = True
    physical_motion: bool = False


class SimulationRuntime:
    """Authoritative software-only embodiment runtime for the reference digital twin."""

    def __init__(self, model: RobotModel, *, step_s: float = 0.02) -> None:
        if step_s <= 0:
            raise ValueError("simulation step must be positive")
        if not model.profile.simulation_only or model.profile.hardware_verified:
            raise ValueError("simulation runtime requires an unverified simulation-only profile")
        self.model = model
        self.step_s = step_s
        self.twin = DigitalTwinRobot(model)
        self.controller = RobotController(model)
        self.embodiment = SimulationBehaviorEmbodimentPlanner(model)
        self.supervisor = build_simulation_supervisor(model)
        self._link: SimulatedProtocolLink | None = None
        self._gateway: RobotGateway | None = None
        self._device: DigitalTwinProtocolDevice | None = None
        self._start_lock = asyncio.Lock()
        self._execution_lock = asyncio.Lock()

    async def close(self) -> None:
        if self._link is not None:
            await self._link.close()
        self._link = None
        self._gateway = None
        self._device = None

    def telemetry(self) -> RobotTelemetry:
        return self.twin.telemetry()

    async def execute_behavior(self, intent: BehaviorIntent) -> SimulationExecutionReport:
        async with self._execution_lock:
            gateway, device = await self._ensure_started()
            goal = self.embodiment.plan(intent)
            planned = self.controller.plan_joint_targets(
                current_joints_deg=self.twin.state.positions_deg,
                target_joints_deg=goal.target_joints_deg,
                sample_period_s=self.step_s,
            )
            candidate, dynamics = planned.terminal_safety_inputs(
                system_state=SystemState.ARMED,
                estop_active=False,
                command_age_ms=0.0,
                heartbeat_age_ms=10.0,
            )
            safety = self.supervisor.evaluate(candidate, dynamics)
            if not safety.approved or safety.authorization is None:
                details = ", ".join(violation.code.value for violation in safety.violations)
                raise SimulationRuntimeError(
                    f"simulation safety rejected behavior {intent.cue.value}: {details}"
                )

            heartbeat_receipt = await self._request_with_device(
                device,
                gateway.send_heartbeat(
                    uptime_ms=self.twin.state.uptime_ms,
                    state=WireSystemState.ARMED,
                ),
            )
            motion_receipt = await self._request_with_device(
                device,
                gateway.send_authorization(safety.authorization),
            )

            steps = 0
            max_steps = 5000
            while self.twin.state.state is not WireSystemState.IDLE and steps < max_steps:
                self.twin.step(self.step_s)
                steps += 1
            if self.twin.state.state is not WireSystemState.IDLE:
                raise SimulationRuntimeError("digital twin failed to settle within simulation budget")

            return SimulationExecutionReport(
                cue=intent.cue.value,
                style=intent.style.value,
                safety_decision=safety.decision,
                authorization_id=safety.authorization.authorization_id,
                heartbeat_ack=heartbeat_receipt.ack_status,
                motion_ack=motion_receipt.ack_status,
                simulation_steps=steps,
                simulated_duration_s=round(steps * self.step_s, 6),
                telemetry=self.twin.telemetry(),
            )

    async def estop(self) -> GatewayReceipt:
        async with self._execution_lock:
            gateway, device = await self._ensure_started()
            receipt = await self._request_with_device(
                device,
                gateway.send_estop(EstopReason.MANUAL),
            )
            self.supervisor.trigger_software_estop("simulation API E-stop")
            return receipt

    def reset_estop(self) -> bool:
        if self.twin.state.state is not WireSystemState.ESTOP:
            return True
        self.twin.reset_estop()
        self.supervisor.observe_heartbeat_age(0.0)
        return self.supervisor.request_manual_reset().cleared

    async def _ensure_started(self) -> tuple[RobotGateway, DigitalTwinProtocolDevice]:
        async with self._start_lock:
            if self._link is None:
                self._link = await SimulatedProtocolLink.create(read_size=32)
                mapping = {
                    name: joint.protocol_id for name, joint in self.model.profile.joints.items()
                }
                self._gateway = RobotGateway(self._link.host, mapping, ack_timeout_s=1.0)
                self._device = DigitalTwinProtocolDevice(self._link.device, self.twin)
            assert self._gateway is not None
            assert self._device is not None
            return self._gateway, self._device

    @staticmethod
    async def _request_with_device(
        device: DigitalTwinProtocolDevice,
        request: Awaitable[GatewayReceipt],
    ) -> GatewayReceipt:
        device_task = asyncio.create_task(device.serve_once())
        try:
            receipt = await request
            await device_task
            return receipt
        except Exception:
            if not device_task.done():
                device_task.cancel()
            raise
