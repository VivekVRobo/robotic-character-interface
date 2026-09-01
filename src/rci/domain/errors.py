"""Domain exception hierarchy."""


class RCIError(Exception):
    """Base class for expected RCI application failures."""


class ConfigurationError(RCIError):
    """Configuration is missing, malformed, or unsafe."""


class ProtocolError(RCIError):
    """A communication packet or protocol transition is invalid."""


class HardwareError(RCIError):
    """A hardware transport or device operation failed."""


class GestureError(RCIError):
    """Gesture processing failed."""


class CognitionError(RCIError):
    """Cognition provider or structured interpretation failed."""


class CharacterError(RCIError):
    """Character loading, canon, or response generation failed."""


class VoiceError(RCIError):
    """Voice capture, recognition, synthesis, or playback failed."""


class MotionError(RCIError):
    """Robot modelling, planning, or execution failed."""


class SafetyViolation(RCIError):
    """A requested action violated a deterministic safety constraint."""


class EmergencyStopError(RCIError):
    """An operation is invalid while emergency stop is active."""
