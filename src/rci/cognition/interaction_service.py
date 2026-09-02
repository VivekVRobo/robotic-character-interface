"""High-level multimodal interaction service above character and behavior boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from rci.behavior.planner import BehaviorIntent, BehaviorPlanner
from rci.characters.client import CharacterEngine
from rci.characters.contracts import CharacterResponseV1
from rci.cognition.meaning import MeaningFrame
from rci.gesture.models import GestureObservation
from rci.multimodal.correlator import MultimodalCorrelator
from rci.voice.models import VoiceTranscript


@dataclass(frozen=True, slots=True)
class InteractionResult:
    meaning: MeaningFrame
    character_response: CharacterResponseV1
    behavior: BehaviorIntent | None


class InteractionService:
    """Correlate inputs, invoke character intelligence, then plan actuator-free behavior."""

    def __init__(
        self,
        character_engine: CharacterEngine,
        *,
        correlator: MultimodalCorrelator | None = None,
        behavior_planner: BehaviorPlanner | None = None,
    ) -> None:
        self.character_engine = character_engine
        self.correlator = MultimodalCorrelator() if correlator is None else correlator
        self.behavior_planner = BehaviorPlanner() if behavior_planner is None else behavior_planner

    async def interact(
        self,
        *,
        timestamp_ms: int,
        text: str | None = None,
        voice: VoiceTranscript | None = None,
        gesture: GestureObservation | None = None,
    ) -> InteractionResult:
        meaning = self.correlator.correlate(
            timestamp_ms=timestamp_ms,
            text=text,
            voice=voice,
            gesture=gesture,
        )
        response = await self.character_engine.respond(meaning)
        behavior = self.behavior_planner.plan(response)
        return InteractionResult(meaning, response, behavior)
