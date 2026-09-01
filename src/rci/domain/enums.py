"""Shared enumerations used across subsystem boundaries."""

from enum import StrEnum


class SystemState(StrEnum):
    BOOT = "BOOT"
    SELF_TEST = "SELF_TEST"
    CALIBRATING = "CALIBRATING"
    IDLE = "IDLE"
    ARMED = "ARMED"
    EXECUTING = "EXECUTING"
    DEGRADED = "DEGRADED"
    FAULT = "FAULT"
    ESTOP = "ESTOP"
    SHUTDOWN = "SHUTDOWN"


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class CharacterName(StrEnum):
    AURELIA = "aurelia"
    KANZAKI = "kanzaki"


class GestureType(StrEnum):
    UNKNOWN = "unknown"
    TILT_LEFT = "tilt_left"
    TILT_RIGHT = "tilt_right"
    TILT_FORWARD = "tilt_forward"
    TILT_BACKWARD = "tilt_backward"
    WAVE = "wave"
    FLICK_LEFT = "flick_left"
    FLICK_RIGHT = "flick_right"
    ROTATION = "rotation"
    HOLD = "hold"
    DOUBLE_MOVEMENT = "double_movement"
    CIRCULAR_MOVEMENT = "circular_movement"


class MotionDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ESTOP = "ESTOP"


class SafetySeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class FaultSeverity(StrEnum):
    RECOVERABLE = "RECOVERABLE"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"


class InteractionMode(StrEnum):
    GESTURE = "gesture"
    VOICE = "voice"
    TEXT = "text"


class RobotMode(StrEnum):
    DISABLED = "DISABLED"
    READY = "READY"
    MOVING = "MOVING"
    SAFE = "SAFE"
    FAULT = "FAULT"


class VoiceState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    RECOGNIZING = "RECOGNIZING"
    SPEAKING = "SPEAKING"
    FAILED = "FAILED"


class BehaviorStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TrajectoryStatus(StrEnum):
    PLANNED = "PLANNED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
