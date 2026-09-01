from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from rci.protocols.constants import AckStatus, MessageType
from rci.protocols.framing import Frame
from rci.protocols.messages import Acknowledgement
from rci.simulation.protocol_link import SimulatedProtocolLink


class FirmwareDispatch(IntEnum):
    REJECTED_INVALID_FRAME = 0
    HEARTBEAT_ACCEPTED = 1
    ESTOP_LATCHED = 2
    MOTION_DEFERRED = 3
    MOTION_REJECTED_UNSAFE = 4
    MESSAGE_IGNORED = 5
    MOTION_REJECTED_INVALID_PAYLOAD = 6


@dataclass(frozen=True, slots=True)
class FirmwareReply:
    dispatch: FirmwareDispatch
    ack_status: AckStatus


@dataclass(frozen=True, slots=True)
class FirmwareExchange:
    request: Frame
    reply: FirmwareReply


class CompiledFirmwareBridge:
    def __init__(self, executable: Path) -> None:
        self._executable = executable
        self._process: asyncio.subprocess.Process | None = None

    async def open(self) -> None:
        if self._process is not None:
            raise RuntimeError("firmware bridge is already open")
        self._process = await asyncio.create_subprocess_exec(
            str(self._executable),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def close(self) -> None:
        process = self._process
        if process is None:
            return
        if process.stdin is not None:
            process.stdin.close()
        await process.wait()
        self._process = None

    async def dispatch(self, frame: Frame, *, now_ms: int) -> FirmwareReply:
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise RuntimeError("firmware bridge is not open")
        if now_ms < 0:
            raise ValueError("now_ms must be non-negative")

        process.stdin.write(f"{now_ms} {frame.encode().hex()}\n".encode())
        await process.stdin.drain()
        line = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
        if not line:
            stderr = b""
            if process.stderr is not None:
                stderr = await process.stderr.read()
            raise RuntimeError(f"firmware bridge exited without a reply: {stderr.decode()}")

        parts = line.decode().strip().split()
        if len(parts) != 2:
            raise RuntimeError(f"invalid firmware bridge reply: {line!r}")
        return FirmwareReply(FirmwareDispatch(int(parts[0])), AckStatus(int(parts[1])))


async def serve_one_firmware_exchange(
    link: SimulatedProtocolLink,
    bridge: CompiledFirmwareBridge,
    *,
    now_ms: int,
) -> FirmwareExchange:
    request = await link.device.receive_frame(timeout_s=1.0)
    reply = await bridge.dispatch(request, now_ms=now_ms)
    response_type = MessageType.ACK if reply.ack_status is AckStatus.OK else MessageType.NACK
    acknowledgement = Acknowledgement(request.sequence, reply.ack_status)
    await link.device.send_frame(Frame(response_type, request.sequence, acknowledgement.encode()))
    return FirmwareExchange(request=request, reply=reply)
