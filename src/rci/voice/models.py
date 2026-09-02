"""Typed voice-recognition and synthesis records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VoiceTranscript:
    text: str
    confidence: float
    simulation: bool


@dataclass(frozen=True, slots=True)
class SpeechPlan:
    text: str
    estimated_duration_s: float
    simulation: bool
    interrupted: bool = False
