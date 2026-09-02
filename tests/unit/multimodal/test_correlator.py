import pytest

from rci.domain.enums import GestureType, InteractionMode
from rci.gesture.models import GestureObservation
from rci.multimodal import MultimodalCorrelator
from rci.voice.models import VoiceTranscript


def _gesture(*, timestamp_ms: int = 1000) -> GestureObservation:
    return GestureObservation(
        gesture=GestureType.WAVE,
        confidence=0.8,
        timestamp_ms=timestamp_ms,
        pitch_deg=0.0,
        roll_deg=15.0,
        angular_speed_deg_s=25.0,
        simulation=True,
    )


def test_voice_and_fresh_gesture_correlate_into_one_meaning_frame() -> None:
    frame = MultimodalCorrelator().correlate(
        timestamp_ms=1000,
        voice=VoiceTranscript("hello aurelia", 0.9, True),
        gesture=_gesture(),
    )
    assert frame.mode is InteractionMode.VOICE
    assert frame.text == "hello aurelia"
    assert frame.gesture is GestureType.WAVE
    assert frame.confidence == 0.8
    assert frame.simulation is True


def test_stale_gesture_is_not_attached_to_text() -> None:
    frame = MultimodalCorrelator(gesture_correlation_window_ms=100).correlate(
        timestamp_ms=1000,
        text="hello",
        gesture=_gesture(timestamp_ms=500),
    )
    assert frame.mode is InteractionMode.TEXT
    assert frame.gesture is None
    assert frame.confidence == 1.0


def test_text_and_voice_are_mutually_exclusive() -> None:
    with pytest.raises(ValueError, match="either text or voice"):
        MultimodalCorrelator().correlate(
            timestamp_ms=1,
            text="text",
            voice=VoiceTranscript("voice", 1.0, True),
        )
