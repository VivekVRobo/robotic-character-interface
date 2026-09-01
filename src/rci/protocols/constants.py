"""RCI binary wire-protocol constants and enumerations."""

from enum import IntEnum

MAGIC = b"RC"
PROTOCOL_VERSION = 1
HEADER_SIZE = 8
CRC_SIZE = 2
FRAME_OVERHEAD = HEADER_SIZE + CRC_SIZE
MAX_PAYLOAD_SIZE = 512
NRF24_MAX_FRAME_SIZE = 32
GLOVE_TELEMETRY_PAYLOAD_SIZE = 21
GLOVE_TELEMETRY_FRAME_SIZE = FRAME_OVERHEAD + GLOVE_TELEMETRY_PAYLOAD_SIZE
MAX_JOINT_TARGETS = 8

assert GLOVE_TELEMETRY_FRAME_SIZE <= NRF24_MAX_FRAME_SIZE


class MessageType(IntEnum):
    GLOVE_TELEMETRY = 0x01
    HEARTBEAT = 0x02
    VALIDATED_MOTION_COMMAND = 0x03
    ESTOP = 0x04
    ACK = 0x05
    NACK = 0x06
    ROBOT_TELEMETRY = 0x07


class DeviceSource(IntEnum):
    HOST = 0x01
    GLOVE = 0x02
    GATEWAY = 0x03
    ROBOT = 0x04


class WireSystemState(IntEnum):
    BOOT = 0x01
    SELF_TEST = 0x02
    CALIBRATING = 0x03
    IDLE = 0x04
    ARMED = 0x05
    EXECUTING = 0x06
    DEGRADED = 0x07
    FAULT = 0x08
    ESTOP = 0x09
    SHUTDOWN = 0x0A


class MotionMode(IntEnum):
    POSITION = 0x01


class EstopReason(IntEnum):
    MANUAL = 0x01
    WATCHDOG = 0x02
    SAFETY = 0x03
    COMMUNICATION = 0x04


class AckStatus(IntEnum):
    OK = 0x00
    REJECTED = 0x01
    STALE = 0x02
    INVALID = 0x03
