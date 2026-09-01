from __future__ import annotations

import pytest

from rci.domain.errors import ProtocolError
from rci.protocols.constants import WireSystemState
from rci.protocols.messages import RobotJointTelemetry, RobotTelemetry


def _telemetry() -> RobotTelemetry:
    return RobotTelemetry(
        uptime_ms=123456,
        state=WireSystemState.EXECUTING,
        flags=3,
        supply_mv=6000,
        joints=(
            RobotJointTelemetry(1, 1250, 240, 210),
            RobotJointTelemetry(2, -350, -120, 180),
            RobotJointTelemetry(3, 9050, 0, 95),
            RobotJointTelemetry(4, 2000, 15, 110),
        ),
    )


def test_robot_telemetry_round_trip() -> None:
    telemetry = _telemetry()
    assert RobotTelemetry.decode(telemetry.encode()) == telemetry


def test_robot_telemetry_rejects_duplicate_joint_ids() -> None:
    telemetry = _telemetry()
    duplicate = RobotTelemetry(
        uptime_ms=telemetry.uptime_ms,
        state=telemetry.state,
        flags=telemetry.flags,
        supply_mv=telemetry.supply_mv,
        joints=(telemetry.joints[0], telemetry.joints[0]),
    )
    with pytest.raises(ProtocolError, match="duplicate joint ids"):
        duplicate.encode()


def test_robot_telemetry_rejects_truncated_payload() -> None:
    with pytest.raises(ProtocolError, match="truncated"):
        RobotTelemetry.decode(b"\x00" * 8)
