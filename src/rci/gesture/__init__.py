"""Gesture telemetry and deterministic motion-gesture recognition pipeline."""

from rci.gesture.classifier import MotionGestureClassifier
from rci.gesture.models import GestureObservation
from rci.gesture.synthetic import synthetic_tilt, synthetic_wave

__all__ = [
    "GestureObservation",
    "MotionGestureClassifier",
    "synthetic_tilt",
    "synthetic_wave",
]
