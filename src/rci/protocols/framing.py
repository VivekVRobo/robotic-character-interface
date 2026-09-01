"""Strict binary framing for serial and compact radio messages."""

from __future__ import annotations

from dataclasses import dataclass
from struct import Struct

from rci.domain.errors import ProtocolChecksumError, ProtocolError
from rci.protocols.checksums import crc16_ccitt_false
from rci.protocols.constants import (
    CRC_SIZE,
    HEADER_SIZE,
    MAGIC,
    MAX_PAYLOAD_SIZE,
    PROTOCOL_VERSION,
    MessageType,
)

_HEADER = Struct("<2sBBHH")
_CRC = Struct("<H")


@dataclass(frozen=True, slots=True)
class Frame:
    """One complete protocol frame with strict length and checksum semantics."""

    message_type: MessageType
    sequence: int
    payload: bytes = b""

    def __post_init__(self) -> None:
        if not 0 <= self.sequence <= 0xFFFF:
            raise ProtocolError("sequence must fit uint16")
        if len(self.payload) > MAX_PAYLOAD_SIZE:
            raise ProtocolError("payload exceeds protocol maximum")

    def encode(self) -> bytes:
        header = _HEADER.pack(
            MAGIC,
            PROTOCOL_VERSION,
            int(self.message_type),
            self.sequence,
            len(self.payload),
        )
        body = header + self.payload
        return body + _CRC.pack(crc16_ccitt_false(body))

    @classmethod
    def decode(cls, data: bytes) -> Frame:
        if len(data) < HEADER_SIZE + CRC_SIZE:
            raise ProtocolError("frame is truncated")

        magic, version, raw_type, sequence, payload_length = _HEADER.unpack_from(data)
        if magic != MAGIC:
            raise ProtocolError("invalid frame magic")
        if version != PROTOCOL_VERSION:
            raise ProtocolError(f"unsupported protocol version: {version}")
        if payload_length > MAX_PAYLOAD_SIZE:
            raise ProtocolError("declared payload exceeds protocol maximum")

        expected_size = HEADER_SIZE + payload_length + CRC_SIZE
        if len(data) != expected_size:
            raise ProtocolError(
                f"frame length mismatch: declared={expected_size}, actual={len(data)}"
            )

        try:
            message_type = MessageType(raw_type)
        except ValueError as exc:
            raise ProtocolError(f"unknown message type: {raw_type}") from exc

        payload_end = HEADER_SIZE + payload_length
        payload = data[HEADER_SIZE:payload_end]
        (received_crc,) = _CRC.unpack_from(data, payload_end)
        calculated_crc = crc16_ccitt_false(data[:payload_end])
        if received_crc != calculated_crc:
            raise ProtocolChecksumError("frame checksum mismatch")

        return cls(message_type=message_type, sequence=sequence, payload=payload)


def encode_frame(message_type: MessageType, sequence: int, payload: bytes = b"") -> bytes:
    return Frame(message_type=message_type, sequence=sequence, payload=payload).encode()


def decode_frame(data: bytes) -> Frame:
    return Frame.decode(data)
