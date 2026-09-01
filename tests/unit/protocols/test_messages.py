from uuid import UUID

import pytest

from rci.domain.errors import ProtocolError
from rci.protocols.constants import (
    GLOVE_TELEMETRY_FRAME_SIZE,
    NRF24_MAX_FRAME_SIZE,
    DeviceSource,
    MessageType,
    MotionMode,
    WireSystemState,
)
from rci.protocols.framing import Frame
from rci.protocols.messages import GloveTelemetry, Heartbeat, JointTarget, ValidatedMotionCommand


def test_glove_payload_round_trip_and_radio_size() -> None:
    telemetry = GloveTelemetry(
        device_time_ms_mod=0x3456,
        accel_x_mg=1000,
        accel_y_mg=-250,
        accel_z_mg=42,
        gyro_x_cdeg_s=1250,
        gyro_y_cdeg_s=-330,
        gyro_z_cdeg_s=0,
        pitch_cdeg=1234,
        roll_cdeg=-567,
        battery_mv=3975,
        flags=5,
    )
    payload = telemetry.encode()
    assert GloveTelemetry.decode(payload) == telemetry
    encoded = Frame(MessageType.GLOVE_TELEMETRY, 0x1234, payload).encode()
    assert len(encoded) == GLOVE_TELEMETRY_FRAME_SIZE == 31
    assert len(encoded) <= NRF24_MAX_FRAME_SIZE


def test_heartbeat_round_trip() -> None:
    heartbeat = Heartbeat(DeviceSource.ROBOT, 123456, WireSystemState.IDLE)
    assert Heartbeat.decode(heartbeat.encode()) == heartbeat


def test_validated_motion_command_round_trip() -> None:
    command = ValidatedMotionCommand(
        command_id=UUID("00112233-4455-6677-8899-aabbccddeeff"),
        ttl_ms=250,
        mode=MotionMode.POSITION,
        targets=(JointTarget(0, 1500), JointTarget(1, -725)),
        max_velocity_cdeg_s=6000,
        max_acceleration_cdeg_s2=18000,
    )
    assert ValidatedMotionCommand.decode(command.encode()) == command


def test_motion_command_rejects_duplicate_joint_ids() -> None:
    command = ValidatedMotionCommand(
        command_id=UUID(int=1),
        ttl_ms=250,
        mode=MotionMode.POSITION,
        targets=(JointTarget(2, 100), JointTarget(2, 200)),
        max_velocity_cdeg_s=100,
        max_acceleration_cdeg_s2=200,
    )
    with pytest.raises(ProtocolError, match="duplicate"):
        command.encode()
