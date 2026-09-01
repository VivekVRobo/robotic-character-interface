"""Structured perception frame sent from RCI inputs to a character engine."""

from __future__ import annotations

from dataclasses import dataclass

from rci.domain.enums import GestureType, InteractionMode


@dataclass(frozen=True, slots=True)
class MeaningFrame:
    text: str
    mode: InteractionMode
    timestamp_ms: int
    confidence: float
    gesture: GestureType | None = None
    simulation: bool = False

    def __post_init__(self) -> None:
        if not self.text.strip() and self.gesture is None:
            raise ValueError("MeaningFrame requires text or a gesture")
        if self.timestamp_ms < 0:
            raise ValueError("MeaningFrame timestamp must be non-negative")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("MeaningFrame confidence must be in [0, 1]")
