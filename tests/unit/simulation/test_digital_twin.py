from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from rci.protocols.constants import MotionMode, WireSystemState
from rci.protocols.messages import JointTarget, RobotTelemetry, ValidatedMotionCommand
from rci.robotics import RobotModel, load_reference_profile
from rci.simulation import DigitalTwinRobot

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "configs" / "simulation" / "reference_arm.yaml"


def _twin() -> DigitalTwinRobot:
    return DigitalTwinRobot(RobotModel(load_reference_profile(PROFILE)))


def _command() -> ValidatedMotionCommand:
    return ValidatedMotionCommand(
        command_id=UUID("00112233-4455-6677-8899-aabbccddeeff"),
        ttl_ms=250,
        mode=MotionMode.POSITION,
        targets=(
            JointTarget(1, 3000),
            JointTarget(2, 4500),
            JointTarget(3, 3000),
            JointTarget(4, 2500),
        ),
        max_velocity_cdeg_s=3000,
        max_acceleration_cdeg_s2=8000,
    )


def test_digital_twin_moves_deterministically_toward_validated_targets() -> None:
    twin = _twin()
    start = twin.state
    twin.accept(_command())
    assert twin.state.state is WireSystemState.EXECUTING

    for _ in range(400):
        state = twin.step(0.01)
        if state.state is WireSystemState.IDLE:
            break

    assert state.state is WireSystemState.IDLE
    assert state.positions_deg["base"] == pytest.approx(30.0, abs=1e-6)
    assert state.positions_deg["shoulder"] == pytest.approx(45.0, abs=1e-6)
    assert state.positions_deg["elbow"] == pytest.approx(30.0, abs=1e-6)
    assert state.positions_deg["gripper"] == pytest.approx(25.0, abs=1e-6)
    assert state.uptime_ms > start.uptime_ms


def test_digital_twin_estop_freezes_motion_until_explicit_reset() -> None:
    twin = _twin()
    twin.accept(_command())
    twin.step(0.05)
    twin.estop()
    frozen = twin.state.positions_deg

    for _ in range(10):
        state = twin.step(0.05)
    assert state.state is WireSystemState.ESTOP
    assert state.positions_deg == frozen
    assert all(value == 0.0 for value in state.velocities_deg_s.values())

    twin.reset_estop()
    assert twin.state.state is WireSystemState.IDLE


def test_digital_twin_telemetry_uses_protocol_v1_codec() -> None:
    twin = _twin()
    twin.accept(_command())
    twin.step(0.1)
    telemetry = twin.telemetry(flags=1)
    decoded = RobotTelemetry.decode(telemetry.encode())

    assert decoded == telemetry
    assert decoded.supply_mv == 6000
    assert len(decoded.joints) == 4
    assert decoded.state is WireSystemState.EXECUTING
