"""Deterministic full-duplex protocol link for software-in-the-loop tests."""

from __future__ import annotations

from dataclasses import dataclass

from rci.hardware.memory_transport import MemoryByteTransport, create_memory_transport_pair
from rci.hardware.protocol_transport import ProtocolTransport


@dataclass(slots=True)
class SimulatedProtocolLink:
    """Connected host/device framed transports with raw fault-injection access."""

    host: ProtocolTransport
    device: ProtocolTransport
    host_bytes: MemoryByteTransport
    device_bytes: MemoryByteTransport

    @classmethod
    async def create(
        cls,
        *,
        capacity_bytes: int = 4096,
        read_size: int = 128,
    ) -> SimulatedProtocolLink:
        host_bytes, device_bytes = create_memory_transport_pair(
            capacity_bytes=capacity_bytes,
            first_name="sim-host",
            second_name="sim-device",
        )
        host = ProtocolTransport(host_bytes, read_size=read_size)
        device = ProtocolTransport(device_bytes, read_size=read_size)
        await host.open()
        await device.open()
        return cls(host, device, host_bytes, device_bytes)

    async def inject_to_device(self, raw_bytes: bytes) -> None:
        """Inject exact raw host-side bytes before protocol decoding."""
        await self.host_bytes.write(raw_bytes)

    async def inject_to_host(self, raw_bytes: bytes) -> None:
        """Inject exact raw device-side bytes before protocol decoding."""
        await self.device_bytes.write(raw_bytes)

    async def close(self) -> None:
        await self.host.close()
        await self.device.close()
