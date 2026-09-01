"""Safety-authorized host gateway for the robot MCU."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from uuid import UUID

from rci.config.models import AppSettings
from rci.domain.errors import HardwareError, ProtocolError
from rci.hardware.protocol_transport import ProtocolTransport
from rci.protocols.constants import (
    AckStatus,
    DeviceSource,
    EstopReason,
    MessageType,
    MotionMode,
    WireSystemState,
)
from rci.protocols.framing import Frame
from rci.protocols.messages import (
    Acknowledgement,
    EmergencyStop,
    Heartbeat,
    JointTarget,
    ValidatedMotionCommand,
)
from rci.safety.supervisor import MotionAuthorization


class RobotGatewayError(HardwareError):
    """Base class for deterministic RobotGateway failures."""


class RobotGatewayRejected(RobotGatewayError):
    """Robot MCU explicitly rejected a host request."""


class RobotGatewayProtocolError(RobotGatewayError):
    """Robot MCU response violated the request/acknowledgement contract."""


@dataclass(frozen=True, slots=True)
class GatewayReceipt:
    """Immutable evidence that the robot MCU acknowledged one host request."""

    frame_sequence: int
    message_type: MessageType
    ack_status: AckStatus
    authorization_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GatewaySnapshot:
    """Small deterministic gateway state surface for diagnostics."""

    is_open: bool
    next_sequence: int
    sent_count: int
    acknowledged_count: int
    rejected_count: int
    last_acknowledged_sequence: int | None


class RobotGateway:
    """Only hardware boundary that turns MotionAuthorization into wire commands."""

    def __init__(
        self,
        transport: ProtocolTransport,
        joint_protocol_ids: Mapping[str, int],
        *,
        ack_timeout_s: float = 0.5,
        initial_sequence: int = 0,
    ) -> None:
        if ack_timeout_s <= 0:
            raise ValueError("ack_timeout_s must be positive")
        if not 0 <= initial_sequence <= 0xFFFF:
            raise ValueError("initial_sequence must fit uint16")
        if not joint_protocol_ids:
            raise ValueError("joint_protocol_ids must not be empty")

        normalized = dict(joint_protocol_ids)
        ids = list(normalized.values())
        if any(not 1 <= protocol_id <= 0xFF for protocol_id in ids):
            raise ValueError("joint protocol ids must be in [1, 255]")
        if len(ids) != len(set(ids)):
            raise ValueError("joint protocol ids must be unique")

        self._transport = transport
        self._joint_protocol_ids = MappingProxyType(normalized)
        self._ack_timeout_s = ack_timeout_s
        self._sequence = initial_sequence
        self._request_lock = asyncio.Lock()
        self._sent_count = 0
        self._acknowledged_count = 0
        self._rejected_count = 0
        self._last_acknowledged_sequence: int | None = None

    @classmethod
    def from_settings(
        cls,
        transport: ProtocolTransport,
        settings: AppSettings,
        *,
        ack_timeout_s: float = 0.5,
        initial_sequence: int = 0,
    ) -> RobotGateway:
        mapping: dict[str, int] = {}
        for name, joint in settings.servos.joints.items():
            if joint.protocol_id is None:
                raise RobotGatewayProtocolError(f"joint {name!r} is missing protocol_id")
            mapping[name] = joint.protocol_id
        return cls(
            transport,
            mapping,
            ack_timeout_s=ack_timeout_s,
            initial_sequence=initial_sequence,
        )

    @property
    def joint_protocol_ids(self) -> Mapping[str, int]:
        return self._joint_protocol_ids

    def snapshot(self) -> GatewaySnapshot:
        return GatewaySnapshot(
            is_open=self._transport.is_open,
            next_sequence=self._sequence,
            sent_count=self._sent_count,
            acknowledged_count=self._acknowledged_count,
            rejected_count=self._rejected_count,
            last_acknowledged_sequence=self._last_acknowledged_sequence,
        )

    async def open(self) -> None:
        await self._transport.open()

    async def close(self) -> None:
        await self._transport.close()

    async def send_authorization(self, authorization: MotionAuthorization) -> GatewayReceipt:
        command = self._encode_authorization(authorization)
        return await self._request(
            MessageType.VALIDATED_MOTION_COMMAND,
            command.encode(),
            authorization_id=authorization.authorization_id,
        )

    async def send_heartbeat(
        self,
        *,
        uptime_ms: int,
        state: WireSystemState,
    ) -> GatewayReceipt:
        heartbeat = Heartbeat(DeviceSource.HOST, uptime_ms, state)
        return await self._request(MessageType.HEARTBEAT, heartbeat.encode())

    async def send_estop(self, reason: EstopReason) -> GatewayReceipt:
        estop = EmergencyStop(DeviceSource.HOST, reason)
        return await self._request(MessageType.ESTOP, estop.encode())

    def _encode_authorization(self, authorization: MotionAuthorization) -> ValidatedMotionCommand:
        targets: list[JointTarget] = []
        for name, angle_deg in authorization.joint_targets_deg.items():
            protocol_id = self._joint_protocol_ids.get(name)
            if protocol_id is None:
                raise RobotGatewayProtocolError(f"authorization references unmapped joint {name!r}")
            target_cdeg = _exact_protocol_integer(
                f"joint {name!r} target",
                angle_deg,
                scale=100,
                minimum=-32768,
                maximum=32767,
            )
            targets.append(JointTarget(protocol_id, target_cdeg))

        targets.sort(key=lambda target: target.joint_id)
        ttl_ms = _exact_protocol_integer(
            "command_ttl_ms",
            authorization.command_ttl_ms,
            scale=1,
            minimum=1,
            maximum=0xFFFF,
        )
        max_velocity = _exact_protocol_integer(
            "max_velocity_deg_s",
            authorization.max_velocity_deg_s,
            scale=100,
            minimum=1,
            maximum=0xFFFF,
        )
        max_acceleration = _exact_protocol_integer(
            "max_acceleration_deg_s2",
            authorization.max_acceleration_deg_s2,
            scale=100,
            minimum=1,
            maximum=0xFFFF,
        )
        return ValidatedMotionCommand(
            command_id=authorization.authorization_id,
            ttl_ms=ttl_ms,
            mode=MotionMode.POSITION,
            targets=tuple(targets),
            max_velocity_cdeg_s=max_velocity,
            max_acceleration_cdeg_s2=max_acceleration,
        )

    async def _request(
        self,
        message_type: MessageType,
        payload: bytes,
        *,
        authorization_id: UUID | None = None,
    ) -> GatewayReceipt:
        if not self._transport.is_open:
            raise RobotGatewayError("robot transport is not open")

        async with self._request_lock:
            sequence = self._next_sequence()
            try:
                await self._transport.send_frame(Frame(message_type, sequence, payload))
            except Exception as exc:
                raise RobotGatewayError(
                    f"robot send failed for sequence {sequence}: {exc}"
                ) from exc
            self._sent_count += 1

            try:
                response = await self._transport.receive_frame(self._ack_timeout_s)
            except Exception as exc:
                raise RobotGatewayError(
                    f"robot acknowledgement failed for sequence {sequence}: {exc}"
                ) from exc

            if response.message_type not in {MessageType.ACK, MessageType.NACK}:
                raise RobotGatewayProtocolError(
                    f"expected ACK/NACK for sequence {sequence}, got {response.message_type.name}"
                )
            try:
                acknowledgement = Acknowledgement.decode(response.payload)
            except ProtocolError as exc:
                raise RobotGatewayProtocolError("robot acknowledgement payload is invalid") from exc
            if acknowledgement.acknowledged_sequence != sequence:
                raise RobotGatewayProtocolError(
                    "robot acknowledgement sequence does not match outstanding request"
                )

            self._last_acknowledged_sequence = sequence
            rejected = (
                response.message_type is MessageType.NACK
                or acknowledgement.status is not AckStatus.OK
            )
            if rejected:
                self._rejected_count += 1
                raise RobotGatewayRejected(
                    f"robot rejected sequence {sequence}: {acknowledgement.status.name}"
                )

            self._acknowledged_count += 1
            return GatewayReceipt(
                frame_sequence=sequence,
                message_type=message_type,
                ack_status=acknowledgement.status,
                authorization_id=authorization_id,
            )

    def _next_sequence(self) -> int:
        sequence = self._sequence
        self._sequence = (self._sequence + 1) & 0xFFFF
        return sequence


def _exact_protocol_integer(
    name: str,
    value: float,
    *,
    scale: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RobotGatewayProtocolError(f"{name} is not numeric") from exc
    if not decimal_value.is_finite():
        raise RobotGatewayProtocolError(f"{name} must be finite")

    scaled = decimal_value * scale
    integral = scaled.to_integral_value()
    if scaled != integral:
        raise RobotGatewayProtocolError(
            f"{name} is not exactly representable at protocol scale {scale}"
        )
    result = int(integral)
    if not minimum <= result <= maximum:
        raise RobotGatewayProtocolError(f"{name} encoded value must be in [{minimum}, {maximum}]")
    return result
