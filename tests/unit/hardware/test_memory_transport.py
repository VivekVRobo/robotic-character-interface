import asyncio

import pytest

from rci.hardware.memory_transport import create_memory_transport_pair
from rci.hardware.transport import (
    TransportCapacityError,
    TransportClosedError,
    TransportTimeoutError,
)


@pytest.mark.asyncio
async def test_memory_transport_round_trip_and_fragmented_reads() -> None:
    first, second = create_memory_transport_pair(capacity_bytes=32)
    await first.open()
    await second.open()

    await first.write(b"abcdef")
    assert await second.read(2) == b"ab"
    assert await second.read(8) == b"cdef"
    assert first.stats.bytes_written == 6
    assert second.stats.bytes_read == 6


@pytest.mark.asyncio
async def test_memory_transport_read_timeout_is_explicit() -> None:
    first, second = create_memory_transport_pair()
    await first.open()
    await second.open()

    with pytest.raises(TransportTimeoutError, match="timed out"):
        await first.read(16, timeout_s=0.01)


@pytest.mark.asyncio
async def test_memory_transport_is_bounded_and_applies_backpressure() -> None:
    first, second = create_memory_transport_pair(capacity_bytes=4)
    await first.open()
    await second.open()

    await first.write(b"abcd")
    blocked = asyncio.create_task(first.write(b"e"))
    await asyncio.sleep(0)
    assert not blocked.done()

    assert await second.read(2) == b"ab"
    await asyncio.wait_for(blocked, timeout=0.1)
    assert await second.read(3) == b"cde"


@pytest.mark.asyncio
async def test_memory_transport_rejects_impossible_single_write() -> None:
    first, second = create_memory_transport_pair(capacity_bytes=4)
    await first.open()
    await second.open()

    with pytest.raises(TransportCapacityError, match="capacity"):
        await first.write(b"12345")


@pytest.mark.asyncio
async def test_remote_close_produces_eof_and_blocks_future_writes() -> None:
    first, second = create_memory_transport_pair()
    await first.open()
    await second.open()

    await first.close()
    assert await second.read(16) == b""
    with pytest.raises(TransportClosedError):
        await second.write(b"data")
