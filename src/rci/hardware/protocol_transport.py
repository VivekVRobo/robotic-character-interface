"""Frame-aware transport wrapper shared by simulated and future physical links."""

from __future__ import annotations

import asyncio
from collections import deque

from rci.domain.errors import ProtocolError
from rci.hardware.transport import (
    AsyncByteTransport,
    TransportClosedError,
    TransportTimeoutError,
)
from rci.protocols.framing import Frame
from rci.protocols.stream import FrameStreamDecoder, StreamIssue


class ProtocolTransport:
    """Send and receive complete protocol frames over an asynchronous byte stream."""

    def __init__(
        self,
        transport: AsyncByteTransport,
        *,
        read_size: int = 128,
        decoder: FrameStreamDecoder | None = None,
    ) -> None:
        if read_size <= 0:
            raise ValueError("read_size must be positive")
        self.transport = transport
        self.read_size = read_size
        self.decoder = decoder or FrameStreamDecoder()
        self._frames: deque[Frame] = deque()
        self._issues: deque[StreamIssue] = deque()

    @property
    def is_open(self) -> bool:
        return self.transport.is_open

    @property
    def pending_frame_count(self) -> int:
        return len(self._frames)

    @property
    def pending_issue_count(self) -> int:
        return len(self._issues)

    async def open(self) -> None:
        await self.transport.open()

    async def close(self) -> None:
        await self.transport.close()

    async def send_frame(self, frame: Frame) -> None:
        await self.transport.write(frame.encode())

    async def receive_frame(self, timeout_s: float | None = None) -> Frame:
        """Return the next frame while surfacing any stream corruption first."""
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be positive when provided")

        async def receive_once() -> Frame:
            while True:
                if self._issues:
                    issue = self._issues.popleft()
                    raise ProtocolError(f"stream {issue.kind.value}: {issue.detail}")
                if self._frames:
                    return self._frames.popleft()

                chunk = await self.transport.read(self.read_size)
                if chunk == b"":
                    raise TransportClosedError("remote transport endpoint closed")
                batch = self.decoder.feed(chunk)
                self._issues.extend(batch.issues)
                self._frames.extend(batch.frames)

        if timeout_s is None:
            return await receive_once()
        try:
            async with asyncio.timeout(timeout_s):
                return await receive_once()
        except TimeoutError as exc:
            raise TransportTimeoutError("protocol frame receive timed out") from exc
