"""Bounded stream decoder for recovering complete protocol frames from arbitrary chunks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from struct import Struct

from rci.domain.errors import ProtocolChecksumError, ProtocolError
from rci.protocols.constants import (
    CRC_SIZE,
    FRAME_OVERHEAD,
    HEADER_SIZE,
    MAGIC,
    MAX_PAYLOAD_SIZE,
    PROTOCOL_VERSION,
    MessageType,
)
from rci.protocols.framing import Frame

_HEADER = Struct("<2sBBHH")


class StreamIssueKind(StrEnum):
    DESYNC = "DESYNC"
    INVALID_HEADER = "INVALID_HEADER"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    INVALID_FRAME = "INVALID_FRAME"
    BUFFER_OVERFLOW = "BUFFER_OVERFLOW"


@dataclass(frozen=True, slots=True)
class StreamIssue:
    kind: StreamIssueKind
    detail: str
    discarded_bytes: int


@dataclass(frozen=True, slots=True)
class DecodeBatch:
    frames: tuple[Frame, ...]
    issues: tuple[StreamIssue, ...]
    buffered_bytes: int


class FrameStreamDecoder:
    """Strictly decode framed messages while bounding memory and reporting corruption."""

    def __init__(self, *, max_buffer_bytes: int = MAX_PAYLOAD_SIZE + FRAME_OVERHEAD + 64) -> None:
        if max_buffer_bytes < FRAME_OVERHEAD:
            raise ValueError("max_buffer_bytes must fit at least one empty frame")
        self.max_buffer_bytes = max_buffer_bytes
        self._buffer = bytearray()

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)

    def reset(self) -> None:
        self._buffer.clear()

    def feed(self, data: bytes) -> DecodeBatch:
        frames: list[Frame] = []
        issues: list[StreamIssue] = []

        if len(self._buffer) + len(data) > self.max_buffer_bytes:
            discarded = len(self._buffer) + len(data)
            self._buffer.clear()
            issues.append(
                StreamIssue(
                    StreamIssueKind.BUFFER_OVERFLOW,
                    "stream buffer limit exceeded; buffered data discarded",
                    discarded,
                )
            )
            return DecodeBatch((), tuple(issues), 0)

        self._buffer.extend(data)
        while True:
            if len(self._buffer) < len(MAGIC):
                break

            if not self._buffer.startswith(MAGIC):
                magic_index = self._buffer.find(MAGIC)
                if magic_index == -1:
                    keep = 1 if self._buffer[-1:] == MAGIC[:1] else 0
                    discarded = len(self._buffer) - keep
                    if discarded:
                        del self._buffer[:discarded]
                        issues.append(
                            StreamIssue(
                                StreamIssueKind.DESYNC,
                                "discarded bytes before protocol magic",
                                discarded,
                            )
                        )
                    break
                del self._buffer[:magic_index]
                issues.append(
                    StreamIssue(
                        StreamIssueKind.DESYNC,
                        "discarded bytes before protocol magic",
                        magic_index,
                    )
                )

            if len(self._buffer) < HEADER_SIZE:
                break

            _, version, raw_type, _sequence, payload_length = _HEADER.unpack_from(self._buffer)
            header_error = self._validate_header(version, raw_type, payload_length)
            if header_error is not None:
                del self._buffer[0]
                issues.append(
                    StreamIssue(
                        StreamIssueKind.INVALID_HEADER,
                        header_error,
                        1,
                    )
                )
                continue

            frame_size = HEADER_SIZE + payload_length + CRC_SIZE
            if frame_size > self.max_buffer_bytes:
                del self._buffer[0]
                issues.append(
                    StreamIssue(
                        StreamIssueKind.INVALID_HEADER,
                        "declared frame exceeds stream buffer limit",
                        1,
                    )
                )
                continue
            if len(self._buffer) < frame_size:
                break

            candidate = bytes(self._buffer[:frame_size])
            try:
                frame = Frame.decode(candidate)
            except ProtocolChecksumError as exc:
                del self._buffer[0]
                issues.append(
                    StreamIssue(
                        StreamIssueKind.CHECKSUM_MISMATCH,
                        str(exc),
                        1,
                    )
                )
                continue
            except ProtocolError as exc:
                del self._buffer[0]
                issues.append(
                    StreamIssue(
                        StreamIssueKind.INVALID_FRAME,
                        str(exc),
                        1,
                    )
                )
                continue

            frames.append(frame)
            del self._buffer[:frame_size]

        return DecodeBatch(tuple(frames), tuple(issues), len(self._buffer))

    @staticmethod
    def _validate_header(version: int, raw_type: int, payload_length: int) -> str | None:
        if version != PROTOCOL_VERSION:
            return f"unsupported protocol version: {version}"
        try:
            MessageType(raw_type)
        except ValueError:
            return f"unknown message type: {raw_type}"
        if payload_length > MAX_PAYLOAD_SIZE:
            return "declared payload exceeds protocol maximum"
        return None
