"""Typed motion-gesture observations derived from raw glove telemetry."""

from __future__ import annotations

from dataclasses import dataclass

from rci.domain.enums import GestureType


@dataclass(frozen=True, slots=True)
class GestureObservation:
    gesture: GestureType
    confidence: float
    timestamp_ms: int
    pitch_deg: float
    roll_deg: float
    angular_speed_deg_s: float
    simulation: bool = False

    @property
    def recognized(self) -> bool:
        return self.gesture is not GestureType.UNKNOWN and self.confidence > 0.0
