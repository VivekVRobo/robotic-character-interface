"""Deterministic correlation of text, simulated voice, and motion gestures."""

from __future__ import annotations

from rci.cognition.meaning import MeaningFrame
from rci.domain.enums import GestureType, InteractionMode
from rci.gesture.models import GestureObservation
from rci.voice.models import VoiceTranscript


class MultimodalCorrelator:
    """Create one typed meaning frame without inventing unavailable sensor evidence."""

    def __init__(self, *, gesture_correlation_window_ms: int = 750) -> None:
        if gesture_correlation_window_ms < 0:
            raise ValueError("gesture correlation window must be non-negative")
        self.gesture_correlation_window_ms = gesture_correlation_window_ms

    def correlate(
        self,
        *,
        timestamp_ms: int,
        text: str | None = None,
        voice: VoiceTranscript | None = None,
        gesture: GestureObservation | None = None,
    ) -> MeaningFrame:
        if timestamp_ms < 0:
            raise ValueError("correlation timestamp must be non-negative")
        if text is not None and voice is not None:
            raise ValueError("provide either text or voice transcript, not both")

        normalized_text = ""
        mode = InteractionMode.GESTURE
        confidence = 0.0
        simulation = False

        if voice is not None:
            normalized_text = voice.text.strip()
            mode = InteractionMode.VOICE
            confidence = voice.confidence
            simulation = voice.simulation
        elif text is not None and text.strip():
            normalized_text = " ".join(text.split())
            mode = InteractionMode.TEXT
            confidence = 1.0

        correlated_gesture: GestureType | None = None
        if gesture is not None and gesture.gesture is not GestureType.UNKNOWN:
            age_ms = abs(timestamp_ms - gesture.timestamp_ms)
            if age_ms <= self.gesture_correlation_window_ms:
                correlated_gesture = gesture.gesture
                simulation = simulation or gesture.simulation
                confidence = (
                    gesture.confidence
                    if not normalized_text
                    else min(confidence, gesture.confidence)
                )

        return MeaningFrame(
            text=normalized_text,
            mode=mode,
            timestamp_ms=timestamp_ms,
            confidence=confidence,
            gesture=correlated_gesture,
            simulation=simulation,
        )
