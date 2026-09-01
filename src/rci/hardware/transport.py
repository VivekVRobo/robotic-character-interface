"""Hardware-agnostic asynchronous byte transport contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from rci.domain.errors import HardwareError


class TransportError(HardwareError):
    """Base class for byte transport failures."""


class TransportClosedError(TransportError):
    """The local endpoint is closed or the remote endpoint disconnected."""


class TransportTimeoutError(TransportError):
    """A transport operation exceeded its explicit deadline."""


class TransportCapacityError(TransportError):
    """A single write can never fit within a bounded transport channel."""


@dataclass(frozen=True, slots=True)
class TransportStats:
    """Monotonic transport counters suitable for diagnostics."""

    bytes_read: int = 0
    bytes_written: int = 0
    open_count: int = 0
    close_count: int = 0


@runtime_checkable
class AsyncByteTransport(Protocol):
    """Minimal interface shared by simulation and future serial transports."""

    @property
    def is_open(self) -> bool: ...

    @property
    def stats(self) -> TransportStats: ...

    async def open(self) -> None: ...

    async def close(self) -> None: ...

    async def write(self, data: bytes) -> None: ...

    async def read(self, max_bytes: int, timeout_s: float | None = None) -> bytes: ...
