import pytest

from rci.domain.errors import ProtocolError
from rci.protocols.constants import MAX_PAYLOAD_SIZE, MessageType
from rci.protocols.framing import Frame


def test_frame_round_trip() -> None:
    frame = Frame(MessageType.HEARTBEAT, sequence=42, payload=b"abc")
    assert Frame.decode(frame.encode()) == frame


def test_frame_rejects_wrong_magic() -> None:
    encoded = bytearray(Frame(MessageType.ACK, 1, b"").encode())
    encoded[0] ^= 0xFF
    with pytest.raises(ProtocolError, match="magic"):
        Frame.decode(bytes(encoded))


def test_frame_rejects_unsupported_version() -> None:
    encoded = bytearray(Frame(MessageType.ACK, 1, b"").encode())
    encoded[2] = 99
    with pytest.raises(ProtocolError, match="version"):
        Frame.decode(bytes(encoded))


def test_frame_rejects_unknown_type() -> None:
    encoded = bytearray(Frame(MessageType.ACK, 1, b"").encode())
    encoded[3] = 0xFE
    body = bytes(encoded[:-2])
    from rci.protocols.checksums import crc16_ccitt_false

    encoded[-2:] = crc16_ccitt_false(body).to_bytes(2, "little")
    with pytest.raises(ProtocolError, match="message type"):
        Frame.decode(bytes(encoded))


def test_frame_rejects_checksum_corruption() -> None:
    encoded = bytearray(Frame(MessageType.HEARTBEAT, 7, b"payload").encode())
    encoded[8] ^= 0x01
    with pytest.raises(ProtocolError, match="checksum"):
        Frame.decode(bytes(encoded))


def test_frame_rejects_truncation_and_extra_bytes() -> None:
    encoded = Frame(MessageType.ACK, 3, b"ok").encode()
    with pytest.raises(ProtocolError, match="length"):
        Frame.decode(encoded[:-1])
    with pytest.raises(ProtocolError, match="length"):
        Frame.decode(encoded + b"x")


def test_frame_rejects_oversized_payload() -> None:
    with pytest.raises(ProtocolError, match="maximum"):
        Frame(MessageType.ACK, 1, b"x" * (MAX_PAYLOAD_SIZE + 1))
