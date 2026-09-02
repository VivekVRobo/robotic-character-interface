"""Protocol device adapter that makes the digital twin behave like a robot endpoint."""

from __future__ import annotations

from dataclasses import dataclass

from rci.domain.errors import ProtocolError
from rci.hardware.protocol_transport import ProtocolTransport
from rci.protocols.constants import AckStatus, MessageType
from rci.protocols.framing import Frame
from rci.protocols.messages import (
    Acknowledgement,
    EmergencyStop,
    Heartbeat,
    ValidatedMotionCommand,
)
from rci.simulation.digital_twin import DigitalTwinError, DigitalTwinRobot


@dataclass(frozen=True, slots=True)
class DigitalTwinExchange:
    request_type: MessageType
    request_sequence: int
    status: AckStatus


class DigitalTwinProtocolDevice:
    """Consume protocol-v1 frames and ACK/NACK them against the deterministic twin."""

    def __init__(self, transport: ProtocolTransport, twin: DigitalTwinRobot) -> None:
        self.transport = transport
        self.twin = twin
        self._response_sequence = 0

    async def serve_once(self, *, timeout_s: float = 1.0) -> DigitalTwinExchange:
        request = await self.transport.receive_frame(timeout_s)
        status = AckStatus.OK
        response_type = MessageType.ACK
        try:
            self._dispatch(request)
        except (ProtocolError, DigitalTwinError, ValueError):
            status = AckStatus.INVALID
            response_type = MessageType.NACK

        acknowledgement = Acknowledgement(request.sequence, status)
        await self.transport.send_frame(
            Frame(response_type, self._next_sequence(), acknowledgement.encode())
        )
        return DigitalTwinExchange(request.message_type, request.sequence, status)

    def _dispatch(self, frame: Frame) -> None:
        if frame.message_type is MessageType.HEARTBEAT:
            Heartbeat.decode(frame.payload)
            return
        if frame.message_type is MessageType.VALIDATED_MOTION_COMMAND:
            self.twin.accept(ValidatedMotionCommand.decode(frame.payload))
            return
        if frame.message_type is MessageType.ESTOP:
            EmergencyStop.decode(frame.payload)
            self.twin.estop()
            return
        raise ProtocolError(f"digital twin does not accept {frame.message_type.name}")

    def _next_sequence(self) -> int:
        sequence = self._response_sequence
        self._response_sequence = (self._response_sequence + 1) & 0xFFFF
        return sequence
