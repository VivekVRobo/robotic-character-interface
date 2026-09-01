"""Typed payload codecs for protocol v1 messages."""

from __future__ import annotations

from dataclasses import dataclass
from struct import Struct
from uuid import UUID

from rci.domain.errors import ProtocolError
from rci.protocols.constants import (
    GLOVE_TELEMETRY_PAYLOAD_SIZE,
    MAX_JOINT_TARGETS,
    AckStatus,
    DeviceSource,
    EstopReason,
    MotionMode,
    WireSystemState,
)

_GLOVE = Struct("<HhhhhhhhhHB")
_HEARTBEAT = Struct("<BIB")
_ESTOP = Struct("<BB")
_ACK = Struct("<HB")
_MOTION_HEAD = Struct("<HBB")
_JOINT_TARGET = Struct("<Bh")
_MOTION_TAIL = Struct("<HH")


@dataclass(frozen=True, slots=True)
class GloveTelemetry:
    device_time_ms_mod: int
    accel_x_mg: int
    accel_y_mg: int
    accel_z_mg: int
    gyro_x_cdeg_s: int
    gyro_y_cdeg_s: int
    gyro_z_cdeg_s: int
    pitch_cdeg: int
    roll_cdeg: int
    battery_mv: int
    flags: int = 0

    def encode(self) -> bytes:
        _require_uint("device_time_ms_mod", self.device_time_ms_mod, 16)
        for name, value in (
            ("accel_x_mg", self.accel_x_mg),
            ("accel_y_mg", self.accel_y_mg),
            ("accel_z_mg", self.accel_z_mg),
            ("gyro_x_cdeg_s", self.gyro_x_cdeg_s),
            ("gyro_y_cdeg_s", self.gyro_y_cdeg_s),
            ("gyro_z_cdeg_s", self.gyro_z_cdeg_s),
            ("pitch_cdeg", self.pitch_cdeg),
            ("roll_cdeg", self.roll_cdeg),
        ):
            _require_int16(name, value)
        _require_uint("battery_mv", self.battery_mv, 16)
        _require_uint("flags", self.flags, 8)
        payload = _GLOVE.pack(
            self.device_time_ms_mod,
            self.accel_x_mg,
            self.accel_y_mg,
            self.accel_z_mg,
            self.gyro_x_cdeg_s,
            self.gyro_y_cdeg_s,
            self.gyro_z_cdeg_s,
            self.pitch_cdeg,
            self.roll_cdeg,
            self.battery_mv,
            self.flags,
        )
        if len(payload) != GLOVE_TELEMETRY_PAYLOAD_SIZE:
            raise ProtocolError("internal glove payload size mismatch")
        return payload

    @classmethod
    def decode(cls, payload: bytes) -> GloveTelemetry:
        if len(payload) != _GLOVE.size:
            raise ProtocolError("invalid glove telemetry payload length")
        values = _GLOVE.unpack(payload)
        return cls(*values)


@dataclass(frozen=True, slots=True)
class Heartbeat:
    source: DeviceSource
    uptime_ms: int
    state: WireSystemState

    def encode(self) -> bytes:
        _require_uint("uptime_ms", self.uptime_ms, 32)
        return _HEARTBEAT.pack(int(self.source), self.uptime_ms, int(self.state))

    @classmethod
    def decode(cls, payload: bytes) -> Heartbeat:
        if len(payload) != _HEARTBEAT.size:
            raise ProtocolError("invalid heartbeat payload length")
        raw_source, uptime_ms, raw_state = _HEARTBEAT.unpack(payload)
        try:
            return cls(DeviceSource(raw_source), uptime_ms, WireSystemState(raw_state))
        except ValueError as exc:
            raise ProtocolError("heartbeat contains an unknown enum value") from exc


@dataclass(frozen=True, slots=True)
class JointTarget:
    joint_id: int
    target_cdeg: int


@dataclass(frozen=True, slots=True)
class ValidatedMotionCommand:
    """Safety-approved semantic joint command for the robot MCU, never PWM."""

    command_id: UUID
    ttl_ms: int
    mode: MotionMode
    targets: tuple[JointTarget, ...]
    max_velocity_cdeg_s: int
    max_acceleration_cdeg_s2: int

    def encode(self) -> bytes:
        _require_uint("ttl_ms", self.ttl_ms, 16, minimum=1)
        _require_uint("max_velocity_cdeg_s", self.max_velocity_cdeg_s, 16, minimum=1)
        _require_uint(
            "max_acceleration_cdeg_s2",
            self.max_acceleration_cdeg_s2,
            16,
            minimum=1,
        )
        if not 1 <= len(self.targets) <= MAX_JOINT_TARGETS:
            raise ProtocolError("motion command has invalid joint target count")
        joint_ids = [target.joint_id for target in self.targets]
        if len(set(joint_ids)) != len(joint_ids):
            raise ProtocolError("motion command contains duplicate joint ids")

        payload = bytearray(self.command_id.bytes)
        payload.extend(_MOTION_HEAD.pack(self.ttl_ms, int(self.mode), len(self.targets)))
        for target in self.targets:
            _require_uint("joint_id", target.joint_id, 8)
            _require_int16("target_cdeg", target.target_cdeg)
            payload.extend(_JOINT_TARGET.pack(target.joint_id, target.target_cdeg))
        payload.extend(_MOTION_TAIL.pack(self.max_velocity_cdeg_s, self.max_acceleration_cdeg_s2))
        return bytes(payload)

    @classmethod
    def decode(cls, payload: bytes) -> ValidatedMotionCommand:
        minimum_size = 16 + _MOTION_HEAD.size + _JOINT_TARGET.size + _MOTION_TAIL.size
        if len(payload) < minimum_size:
            raise ProtocolError("motion command payload is truncated")

        command_id = UUID(bytes=payload[:16])
        ttl_ms, raw_mode, joint_count = _MOTION_HEAD.unpack_from(payload, 16)
        if not 1 <= joint_count <= MAX_JOINT_TARGETS:
            raise ProtocolError("motion command has invalid joint target count")
        expected_size = (
            16 + _MOTION_HEAD.size + joint_count * _JOINT_TARGET.size + _MOTION_TAIL.size
        )
        if len(payload) != expected_size:
            raise ProtocolError("motion command payload length mismatch")

        try:
            mode = MotionMode(raw_mode)
        except ValueError as exc:
            raise ProtocolError("unknown motion command mode") from exc

        offset = 16 + _MOTION_HEAD.size
        targets: list[JointTarget] = []
        for _ in range(joint_count):
            joint_id, target_cdeg = _JOINT_TARGET.unpack_from(payload, offset)
            targets.append(JointTarget(joint_id, target_cdeg))
            offset += _JOINT_TARGET.size
        max_velocity, max_acceleration = _MOTION_TAIL.unpack_from(payload, offset)
        decoded = cls(
            command_id=command_id,
            ttl_ms=ttl_ms,
            mode=mode,
            targets=tuple(targets),
            max_velocity_cdeg_s=max_velocity,
            max_acceleration_cdeg_s2=max_acceleration,
        )
        decoded.encode()
        return decoded


@dataclass(frozen=True, slots=True)
class EmergencyStop:
    source: DeviceSource
    reason: EstopReason

    def encode(self) -> bytes:
        return _ESTOP.pack(int(self.source), int(self.reason))

    @classmethod
    def decode(cls, payload: bytes) -> EmergencyStop:
        if len(payload) != _ESTOP.size:
            raise ProtocolError("invalid E-stop payload length")
        source, reason = _ESTOP.unpack(payload)
        try:
            return cls(DeviceSource(source), EstopReason(reason))
        except ValueError as exc:
            raise ProtocolError("E-stop contains an unknown enum value") from exc


@dataclass(frozen=True, slots=True)
class Acknowledgement:
    acknowledged_sequence: int
    status: AckStatus

    def encode(self) -> bytes:
        _require_uint("acknowledged_sequence", self.acknowledged_sequence, 16)
        return _ACK.pack(self.acknowledged_sequence, int(self.status))

    @classmethod
    def decode(cls, payload: bytes) -> Acknowledgement:
        if len(payload) != _ACK.size:
            raise ProtocolError("invalid acknowledgement payload length")
        sequence, raw_status = _ACK.unpack(payload)
        try:
            return cls(sequence, AckStatus(raw_status))
        except ValueError as exc:
            raise ProtocolError("acknowledgement contains an unknown status") from exc


def _require_uint(name: str, value: int, bits: int, *, minimum: int = 0) -> None:
    maximum = (1 << bits) - 1
    if not minimum <= value <= maximum:
        raise ProtocolError(f"{name} must be in [{minimum}, {maximum}]")


def _require_int16(name: str, value: int) -> None:
    if not -32768 <= value <= 32767:
        raise ProtocolError(f"{name} must fit int16")
