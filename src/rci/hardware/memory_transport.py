"""Bounded deterministic in-memory implementation of the byte transport contract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from rci.hardware.transport import (
    TransportCapacityError,
    TransportClosedError,
    TransportStats,
    TransportTimeoutError,
)


class _MemoryChannel:
    """One bounded direction of a full-duplex in-memory link."""

    def __init__(self, capacity_bytes: int) -> None:
        if capacity_bytes <= 0:
            raise ValueError("capacity_bytes must be positive")
        self.capacity_bytes = capacity_bytes
        self._buffer = bytearray()
        self._closed = False
        self._condition = asyncio.Condition()

    async def write(self, data: bytes) -> None:
        if len(data) > self.capacity_bytes:
            raise TransportCapacityError(
                f"write of {len(data)} bytes exceeds channel capacity {self.capacity_bytes}"
            )
        if not data:
            return

        async with self._condition:
            while not self._closed and len(self._buffer) + len(data) > self.capacity_bytes:
                await self._condition.wait()
            if self._closed:
                raise TransportClosedError("remote memory transport endpoint is closed")
            self._buffer.extend(data)
            self._condition.notify_all()

    async def read(self, max_bytes: int, timeout_s: float | None) -> bytes:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be positive when provided")

        async def read_once() -> bytes:
            async with self._condition:
                while not self._buffer and not self._closed:
                    await self._condition.wait()
                if not self._buffer and self._closed:
                    return b""
                count = min(max_bytes, len(self._buffer))
                data = bytes(self._buffer[:count])
                del self._buffer[:count]
                self._condition.notify_all()
                return data

        if timeout_s is None:
            return await read_once()
        try:
            async with asyncio.timeout(timeout_s):
                return await read_once()
        except TimeoutError as exc:
            raise TransportTimeoutError("memory transport read timed out") from exc

    async def close(self) -> None:
        async with self._condition:
            self._closed = True
            self._condition.notify_all()


@dataclass(slots=True)
class MemoryByteTransport:
    """One side of a deterministic full-duplex in-memory byte link."""

    name: str
    _incoming: _MemoryChannel
    _outgoing: _MemoryChannel
    _is_open: bool = False
    _terminally_closed: bool = False
    _bytes_read: int = 0
    _bytes_written: int = 0
    _open_count: int = 0
    _close_count: int = 0

    @property
    def is_open(self) -> bool:
        return self._is_open and not self._terminally_closed

    @property
    def stats(self) -> TransportStats:
        return TransportStats(
            bytes_read=self._bytes_read,
            bytes_written=self._bytes_written,
            open_count=self._open_count,
            close_count=self._close_count,
        )

    async def open(self) -> None:
        if self._terminally_closed:
            raise TransportClosedError("memory transport cannot be reopened after close")
        if not self._is_open:
            self._is_open = True
            self._open_count += 1

    async def close(self) -> None:
        if self._terminally_closed:
            return
        self._is_open = False
        self._terminally_closed = True
        self._close_count += 1
        await self._incoming.close()
        await self._outgoing.close()

    async def write(self, data: bytes) -> None:
        self._require_open()
        await self._outgoing.write(data)
        self._bytes_written += len(data)

    async def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes:
        self._require_open()
        data = await self._incoming.read(max_bytes, timeout_s)
        self._bytes_read += len(data)
        return data

    def _require_open(self) -> None:
        if not self.is_open:
            raise TransportClosedError(f"memory transport {self.name!r} is closed")


def create_memory_transport_pair(
    *,
    capacity_bytes: int = 4096,
    first_name: str = "host",
    second_name: str = "device",
) -> tuple[MemoryByteTransport, MemoryByteTransport]:
    """Return two connected one-shot full-duplex memory transport endpoints."""
    first_to_second = _MemoryChannel(capacity_bytes)
    second_to_first = _MemoryChannel(capacity_bytes)
    first = MemoryByteTransport(
        name=first_name,
        _incoming=second_to_first,
        _outgoing=first_to_second,
    )
    second = MemoryByteTransport(
        name=second_name,
        _incoming=first_to_second,
        _outgoing=second_to_first,
    )
    return first, second
