import pytest

from rci.domain.enums import VoiceState
from rci.voice import EnergyVad, VoiceService, VoiceServiceError


def test_energy_vad_distinguishes_silence_and_signal() -> None:
    vad = EnergyVad(rms_threshold=100.0)
    assert vad.is_speech([0, 0, 0, 0]) is False
    assert vad.is_speech([200, -200, 200, -200]) is True


def test_simulated_voice_turn_and_barge_in() -> None:
    service = VoiceService(barge_in=True)
    speech = service.speak("Aurelia is speaking.")
    assert service.state is VoiceState.SPEAKING
    assert speech.simulation is True

    transcript = service.recognize_simulated("interrupt please", confidence=0.9)
    assert service.state is VoiceState.IDLE
    assert transcript.text == "interrupt please"
    assert transcript.simulation is True


def test_voice_rejects_barge_in_when_disabled() -> None:
    service = VoiceService(barge_in=False)
    service.speak("Speaking")
    with pytest.raises(VoiceServiceError, match="barge-in"):
        service.recognize_simulated("interrupt")
