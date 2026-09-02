from rci.domain.enums import GestureType
from rci.gesture import MotionGestureClassifier, synthetic_tilt, synthetic_wave


def test_classifier_recognizes_tilt_without_inventing_hand_shape() -> None:
    classifier = MotionGestureClassifier()
    observation = classifier.classify(synthetic_tilt(roll_deg=18.0), simulation=True)

    assert observation.gesture is GestureType.TILT_RIGHT
    assert observation.simulation is True
    assert observation.confidence > 0.0


def test_classifier_recognizes_synthetic_wave() -> None:
    classifier = MotionGestureClassifier()
    observation = None
    for sample in synthetic_wave():
        observation = classifier.classify(sample, simulation=True)

    assert observation is not None
    assert observation.gesture is GestureType.WAVE
    assert observation.simulation is True


def test_classifier_keeps_neutral_motion_unknown() -> None:
    observation = MotionGestureClassifier().classify(synthetic_tilt(), simulation=True)
    assert observation.gesture is GestureType.UNKNOWN
    assert observation.confidence == 0.0
