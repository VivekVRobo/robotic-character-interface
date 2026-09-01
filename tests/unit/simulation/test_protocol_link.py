import pytest

from rci.protocols.constants import MessageType
from rci.protocols.framing import Frame
from rci.simulation.protocol_link import SimulatedProtocolLink


@pytest.mark.asyncio
async def test_simulated_link_is_bidirectional() -> None:
    link = await SimulatedProtocolLink.create(read_size=4)
    host_frame = Frame(MessageType.HEARTBEAT, 1, b"host")
    device_frame = Frame(MessageType.ACK, 2, b"device")

    await link.host.send_frame(host_frame)
    await link.device.send_frame(device_frame)

    assert await link.device.receive_frame(timeout_s=0.1) == host_frame
    assert await link.host.receive_frame(timeout_s=0.1) == device_frame
    await link.close()


@pytest.mark.asyncio
async def test_raw_injection_preserves_following_valid_frame_for_recovery() -> None:
    link = await SimulatedProtocolLink.create(read_size=128)
    expected = Frame(MessageType.ACK, 22, b"recovered")

    corrupted = bytearray(Frame(MessageType.ACK, 21, b"broken").encode())
    corrupted[-1] ^= 0x80
    await link.inject_to_host(bytes(corrupted) + expected.encode())

    with pytest.raises(Exception):
        await link.host.receive_frame(timeout_s=0.1)
    assert await link.host.receive_frame(timeout_s=0.1) == expected
    await link.close()
