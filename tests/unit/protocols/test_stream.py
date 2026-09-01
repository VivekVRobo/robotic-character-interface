from struct import Struct

from rci.protocols.constants import MAGIC, MAX_PAYLOAD_SIZE, PROTOCOL_VERSION, MessageType
from rci.protocols.framing import Frame
from rci.protocols.stream import FrameStreamDecoder, StreamIssueKind

_HEADER = Struct("<2sBBHH")


def test_stream_decoder_accepts_frame_one_byte_at_a_time() -> None:
    expected = Frame(MessageType.HEARTBEAT, 42, b"abcdef")
    decoder = FrameStreamDecoder()
    frames = []
    issues = []

    for byte in expected.encode():
        batch = decoder.feed(bytes([byte]))
        frames.extend(batch.frames)
        issues.extend(batch.issues)

    assert frames == [expected]
    assert issues == []
    assert decoder.buffered_bytes == 0


def test_stream_decoder_extracts_multiple_frames_from_one_chunk() -> None:
    first = Frame(MessageType.ACK, 1, b"a")
    second = Frame(MessageType.HEARTBEAT, 2, b"bc")
    batch = FrameStreamDecoder().feed(first.encode() + second.encode())

    assert batch.frames == (first, second)
    assert batch.issues == ()


def test_stream_decoder_reports_garbage_and_recovers_valid_frame() -> None:
    expected = Frame(MessageType.ACK, 9, b"ok")
    batch = FrameStreamDecoder().feed(b"noise" + expected.encode())

    assert batch.frames == (expected,)
    assert any(issue.kind == StreamIssueKind.DESYNC for issue in batch.issues)


def test_stream_decoder_reports_bad_crc_then_recovers_next_frame() -> None:
    bad = bytearray(Frame(MessageType.ACK, 3, b"bad").encode())
    bad[-1] ^= 0xFF
    expected = Frame(MessageType.HEARTBEAT, 4, b"good")
    batch = FrameStreamDecoder().feed(bytes(bad) + expected.encode())

    assert batch.frames == (expected,)
    assert any(issue.kind == StreamIssueKind.CHECKSUM_MISMATCH for issue in batch.issues)


def test_stream_decoder_rejects_oversized_header_without_waiting_for_payload() -> None:
    invalid_header = _HEADER.pack(
        MAGIC,
        PROTOCOL_VERSION,
        int(MessageType.ACK),
        1,
        MAX_PAYLOAD_SIZE + 1,
    )
    batch = FrameStreamDecoder().feed(invalid_header)

    assert any(issue.kind == StreamIssueKind.INVALID_HEADER for issue in batch.issues)
    assert batch.buffered_bytes < len(invalid_header)


def test_stream_decoder_drops_data_on_buffer_overflow() -> None:
    decoder = FrameStreamDecoder(max_buffer_bytes=16)
    batch = decoder.feed(b"x" * 17)

    assert batch.frames == ()
    assert batch.buffered_bytes == 0
    assert batch.issues[0].kind == StreamIssueKind.BUFFER_OVERFLOW
    assert batch.issues[0].discarded_bytes == 17
