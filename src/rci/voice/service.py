"""Voice service abstractions with deterministic software-only backends."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from math import sqrt

from rci.domain.enums import VoiceState
from rci.voice.models import SpeechPlan, VoiceTranscript


class VoiceServiceError(ValueError):
    """Raised when a voice interaction violates the service contract."""


class EnergyVad:
    """Simple deterministic PCM-energy VAD used for tests and backend-independent gating."""

    def __init__(self, *, rms_threshold: float = 350.0) -> None:
        if rms_threshold <= 0:
            raise ValueError("VAD RMS threshold must be positive")
        self.rms_threshold = rms_threshold

    def is_speech(self, pcm16: Sequence[int]) -> bool:
        if not pcm16:
            return False
        if any(sample < -32768 or sample > 32767 for sample in pcm16):
            raise VoiceServiceError("PCM sample must fit signed int16")
        rms = sqrt(sum(float(sample) * float(sample) for sample in pcm16) / len(pcm16))
        return rms >= self.rms_threshold


class SimulationVoiceBackend:
    """Deterministic transcript/TTS planner. It creates no fake microphone or human audio."""

    def recognize(self, text: str, *, confidence: float = 1.0) -> VoiceTranscript:
        normalized = " ".join(text.split())
        if not normalized:
            raise VoiceServiceError("simulated transcript cannot be empty")
        if not 0.0 <= confidence <= 1.0:
            raise VoiceServiceError("voice confidence must be in [0, 1]")
        return VoiceTranscript(normalized, confidence, True)

    def synthesize(self, text: str) -> SpeechPlan:
        normalized = " ".join(text.split())
        if not normalized:
            raise VoiceServiceError("speech text cannot be empty")
        word_count = len(normalized.split())
        duration = max(0.25, word_count / 2.6)
        return SpeechPlan(normalized, duration, True)


class VoiceService:
    """Stateful voice-turn coordinator with explicit barge-in behavior."""

    def __init__(
        self,
        backend: SimulationVoiceBackend | None = None,
        *,
        barge_in: bool = True,
    ) -> None:
        self.backend = SimulationVoiceBackend() if backend is None else backend
        self.barge_in = barge_in
        self.state = VoiceState.IDLE
        self.last_transcript: VoiceTranscript | None = None
        self.active_speech: SpeechPlan | None = None

    def recognize_simulated(self, text: str, *, confidence: float = 1.0) -> VoiceTranscript:
        if self.state is VoiceState.SPEAKING:
            if not self.barge_in:
                raise VoiceServiceError("cannot recognize while speaking when barge-in is disabled")
            self.interrupt()
        self.state = VoiceState.RECOGNIZING
        try:
            transcript = self.backend.recognize(text, confidence=confidence)
        except Exception:
            self.state = VoiceState.FAILED
            raise
        self.last_transcript = transcript
        self.state = VoiceState.IDLE
        return transcript

    def speak(self, text: str) -> SpeechPlan:
        if self.state not in {VoiceState.IDLE, VoiceState.LISTENING}:
            raise VoiceServiceError(f"cannot begin speech from state {self.state}")
        self.state = VoiceState.SPEAKING
        try:
            plan = self.backend.synthesize(text)
        except Exception:
            self.state = VoiceState.FAILED
            raise
        self.active_speech = plan
        return plan

    def complete_speech(self) -> SpeechPlan:
        if self.state is not VoiceState.SPEAKING or self.active_speech is None:
            raise VoiceServiceError("no speech is active")
        completed = self.active_speech
        self.active_speech = None
        self.state = VoiceState.IDLE
        return completed

    def interrupt(self) -> SpeechPlan | None:
        if self.active_speech is None:
            self.state = VoiceState.IDLE
            return None
        interrupted = replace(self.active_speech, interrupted=True)
        self.active_speech = None
        self.state = VoiceState.IDLE
        return interrupted
