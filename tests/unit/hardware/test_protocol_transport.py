import pytest

from rci.domain.errors import ProtocolError
from rci.hardware.transport import TransportClosedError, TransportTimeoutError
from rci.protocols.constants import MessageType
from rci.protocols.framing import Frame
from rci.simulation.protocol_link import SimulatedProtocolLink


@pytest.mark.asyncio
async def test_protocol_transport_round_trip_with_fragmented_reads() -> None:
    link = await SimulatedProtocolLink.create(read_size=3)
    expected = Frame(MessageType.HEARTBEAT, 7, b"heartbeat")

    await link.host.send_frame(expected)
    assert await link.device.receive_frame(timeout_s=0.1) == expected
    await link.close()


@pytest.mark.asyncio
async def test_protocol_transport_surfaces_corruption_before_recovered_frame() -> None:
    link = await SimulatedProtocolLink.create(read_size=128)
    expected = Frame(MessageType.ACK, 11, b"ok")

    await link.inject_to_device(b"garbage" + expected.encode())
    with pytest.raises(ProtocolError, match="DESYNC"):
        await link.device.receive_frame(timeout_s=0.1)
    assert await link.device.receive_frame(timeout_s=0.1) == expected
    await link.close()


@pytest.mark.asyncio
async def test_protocol_transport_timeout_is_explicit() -> None:
    link = await SimulatedProtocolLink.create()

    with pytest.raises(TransportTimeoutError, match="timed out"):
        await link.host.receive_frame(timeout_s=0.01)
    await link.close()


@pytest.mark.asyncio
async def test_protocol_transport_remote_close_is_explicit() -> None:
    link = await SimulatedProtocolLink.create()
    await link.host.close()

    with pytest.raises(TransportClosedError, match="remote"):
        await link.device.receive_frame(timeout_s=0.1)
