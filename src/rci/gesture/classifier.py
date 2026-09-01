"""Deterministic V1 motion-gesture classifier for MPU6050-style telemetry."""

from __future__ import annotations

from collections import deque
from math import sqrt

from rci.domain.enums import GestureType
from rci.gesture.models import GestureObservation
from rci.protocols.messages import GloveTelemetry


class MotionGestureClassifier:
    """Classify motion gestures only; it never infers finger/hand-shape gestures."""

    def __init__(
        self,
        *,
        tilt_threshold_deg: float = 12.0,
        flick_threshold_deg_s: float = 110.0,
        rotation_threshold_deg_s: float = 90.0,
        hold_rate_deg_s: float = 8.0,
        wave_window: int = 8,
    ) -> None:
        if min(tilt_threshold_deg, flick_threshold_deg_s, rotation_threshold_deg_s) <= 0:
            raise ValueError("gesture thresholds must be positive")
        if hold_rate_deg_s < 0 or wave_window < 4:
            raise ValueError("invalid hold rate or wave window")
        self.tilt_threshold_deg = tilt_threshold_deg
        self.flick_threshold_deg_s = flick_threshold_deg_s
        self.rotation_threshold_deg_s = rotation_threshold_deg_s
        self.hold_rate_deg_s = hold_rate_deg_s
        self._roll_history: deque[float] = deque(maxlen=wave_window)

    def classify(self, telemetry: GloveTelemetry, *, simulation: bool = False) -> GestureObservation:
        pitch = telemetry.pitch_cdeg / 100.0
        roll = telemetry.roll_cdeg / 100.0
        gx = telemetry.gyro_x_cdeg_s / 100.0
        gy = telemetry.gyro_y_cdeg_s / 100.0
        gz = telemetry.gyro_z_cdeg_s / 100.0
        angular_speed = sqrt(gx * gx + gy * gy + gz * gz)
        self._roll_history.append(roll)

        gesture = GestureType.UNKNOWN
        confidence = 0.0

        if self._is_wave():
            gesture = GestureType.WAVE
            confidence = 0.9
        elif abs(gz) >= self.rotation_threshold_deg_s:
            gesture = GestureType.ROTATION
            confidence = min(1.0, abs(gz) / (self.rotation_threshold_deg_s * 1.8))
        elif abs(gy) >= self.flick_threshold_deg_s:
            gesture = GestureType.FLICK_RIGHT if gy > 0 else GestureType.FLICK_LEFT
            confidence = min(1.0, abs(gy) / (self.flick_threshold_deg_s * 1.8))
        elif roll >= self.tilt_threshold_deg:
            gesture = GestureType.TILT_RIGHT
            confidence = min(1.0, roll / (self.tilt_threshold_deg * 2.0))
        elif roll <= -self.tilt_threshold_deg:
            gesture = GestureType.TILT_LEFT
            confidence = min(1.0, abs(roll) / (self.tilt_threshold_deg * 2.0))
        elif pitch >= self.tilt_threshold_deg:
            gesture = GestureType.TILT_FORWARD
            confidence = min(1.0, pitch / (self.tilt_threshold_deg * 2.0))
        elif pitch <= -self.tilt_threshold_deg:
            gesture = GestureType.TILT_BACKWARD
            confidence = min(1.0, abs(pitch) / (self.tilt_threshold_deg * 2.0))
        elif angular_speed <= self.hold_rate_deg_s and (
            abs(pitch) >= self.tilt_threshold_deg / 2.0
            or abs(roll) >= self.tilt_threshold_deg / 2.0
        ):
            gesture = GestureType.HOLD
            confidence = 0.7

        return GestureObservation(
            gesture=gesture,
            confidence=confidence,
            timestamp_ms=telemetry.device_time_ms_mod,
            pitch_deg=pitch,
            roll_deg=roll,
            angular_speed_deg_s=angular_speed,
            simulation=simulation,
        )

    def _is_wave(self) -> bool:
        if len(self._roll_history) < self._roll_history.maxlen:
            return False
        threshold = self.tilt_threshold_deg * 0.65
        signs: list[int] = []
        for value in self._roll_history:
            if value >= threshold:
                signs.append(1)
            elif value <= -threshold:
                signs.append(-1)
        if len(signs) < 4:
            return False
        transitions = sum(first != second for first, second in zip(signs, signs[1:], strict=False))
        return transitions >= 3
