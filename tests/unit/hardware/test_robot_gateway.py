import asyncio
from uuid import UUID

import pytest

from rci.hardware.robot_gateway import (
    RobotGateway,
    RobotGatewayError,
    RobotGatewayProtocolError,
    RobotGatewayRejected,
)
from rci.protocols.constants import AckStatus, MessageType, WireSystemState
from rci.protocols.framing import Frame
from rci.protocols.messages import Acknowledgement, ValidatedMotionCommand
from rci.safety.models import CartesianPoint
from rci.safety.supervisor import MotionAuthorization
from rci.simulation.protocol_link import SimulatedProtocolLink


def _authorization(**overrides: object) -> MotionAuthorization:
    values: dict[str, object] = {
        "authorization_id": UUID("00112233-4455-6677-8899-aabbccddeeff"),
        "lifecycle_sequence": 7,
        "joint_targets_deg": {"shoulder": 20.0, "base": 10.25},
        "workspace_point_mm": CartesianPoint(100.0, 0.0, 200.0),
        "command_ttl_ms": 250.0,
        "max_velocity_deg_s": 60.0,
        "max_acceleration_deg_s2": 180.0,
    }
    values.update(overrides)
    return MotionAuthorization(**values)  # type: ignore[arg-type]


async def _ack_once(
    link: SimulatedProtocolLink,
    *,
    status: AckStatus = AckStatus.OK,
    response_type: MessageType = MessageType.ACK,
    sequence_offset: int = 0,
) -> Frame:
    request = await link.device.receive_frame(0.2)
    acknowledgement = Acknowledgement(
        (request.sequence + sequence_offset) & 0xFFFF,
        status,
    )
    await link.device.send_frame(Frame(response_type, 900, acknowledgement.encode()))
    return request


@pytest.mark.asyncio
async def test_authorization_becomes_validated_motion_only_inside_gateway() -> None:
    link = await SimulatedProtocolLink.create()
    gateway = RobotGateway(link.host, {"base": 1, "shoulder": 2})
    peer = asyncio.create_task(_ack_once(link))

    receipt = await gateway.send_authorization(_authorization())
    request = await peer
    command = ValidatedMotionCommand.decode(request.payload)

    assert request.message_type is MessageType.VALIDATED_MOTION_COMMAND
    assert command.command_id == UUID("00112233-4455-6677-8899-aabbccddeeff")
    assert [(target.joint_id, target.target_cdeg) for target in command.targets] == [
        (1, 1025),
        (2, 2000),
    ]
    assert command.ttl_ms == 250
    assert command.max_velocity_cdeg_s == 6000
    assert command.max_acceleration_cdeg_s2 == 18000
    assert receipt.authorization_id == command.command_id
    assert gateway.snapshot().acknowledged_count == 1
    await link.close()


@pytest.mark.asyncio
async def test_nack_rejects_authorization() -> None:
    link = await SimulatedProtocolLink.create()
    gateway = RobotGateway(link.host, {"base": 1, "shoulder": 2})
    peer = asyncio.create_task(
        _ack_once(link, status=AckStatus.REJECTED, response_type=MessageType.NACK)
    )

    with pytest.raises(RobotGatewayRejected, match="REJECTED"):
        await gateway.send_authorization(_authorization())

    await peer
    assert gateway.snapshot().rejected_count == 1
    await link.close()


@pytest.mark.asyncio
async def test_ack_sequence_mismatch_fails_closed() -> None:
    link = await SimulatedProtocolLink.create()
    gateway = RobotGateway(link.host, {"base": 1, "shoulder": 2})
    peer = asyncio.create_task(_ack_once(link, sequence_offset=1))

    with pytest.raises(RobotGatewayProtocolError, match="does not match"):
        await gateway.send_authorization(_authorization())

    await peer
    await link.close()


@pytest.mark.asyncio
async def test_missing_ack_times_out() -> None:
    link = await SimulatedProtocolLink.create()
    gateway = RobotGateway(
        link.host,
        {"base": 1, "shoulder": 2},
        ack_timeout_s=0.01,
    )

    with pytest.raises(RobotGatewayError, match="acknowledgement failed"):
        await gateway.send_authorization(_authorization())

    await link.close()


def test_unknown_joint_mapping_is_rejected_before_transport() -> None:
    link_mapping = {"base": 1}
    gateway = RobotGateway.__new__(RobotGateway)
    # Exercise the normal constructor path without needing an open async link.
    from rci.hardware.memory_transport import create_memory_transport_pair
    from rci.hardware.protocol_transport import ProtocolTransport

    host, _ = create_memory_transport_pair()
    gateway = RobotGateway(ProtocolTransport(host), link_mapping)

    with pytest.raises(RobotGatewayProtocolError, match="unmapped joint"):
        gateway._encode_authorization(_authorization())


def test_non_exact_centidegree_target_is_rejected_not_rounded() -> None:
    from rci.hardware.memory_transport import create_memory_transport_pair
    from rci.hardware.protocol_transport import ProtocolTransport

    host, _ = create_memory_transport_pair()
    gateway = RobotGateway(ProtocolTransport(host), {"base": 1, "shoulder": 2})
    authorization = _authorization(joint_targets_deg={"base": 10.123, "shoulder": 20.0})

    with pytest.raises(RobotGatewayProtocolError, match="exactly representable"):
        gateway._encode_authorization(authorization)


@pytest.mark.asyncio
async def test_host_heartbeat_requires_explicit_ack() -> None:
    link = await SimulatedProtocolLink.create()
    gateway = RobotGateway(link.host, {"base": 1})
    peer = asyncio.create_task(_ack_once(link))

    receipt = await gateway.send_heartbeat(uptime_ms=1234, state=WireSystemState.ARMED)
    request = await peer

    assert request.message_type is MessageType.HEARTBEAT
    assert receipt.message_type is MessageType.HEARTBEAT
    await link.close()
