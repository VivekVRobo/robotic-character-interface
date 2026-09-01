"""Host/firmware communication contracts."""

from rci.protocols.checksums import crc16_ccitt_false
from rci.protocols.constants import MessageType, PROTOCOL_VERSION
from rci.protocols.framing import Frame, decode_frame, encode_frame

__all__ = [
    "Frame",
    "MessageType",
    "PROTOCOL_VERSION",
    "crc16_ccitt_false",
    "decode_frame",
    "encode_frame",
]
