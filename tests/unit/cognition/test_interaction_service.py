import pytest

from rci.characters.contracts import CharacterResponseV1
from rci.cognition.interaction_service import InteractionService
from rci.cognition.meaning import MeaningFrame
from rci.domain.enums import GestureType
from rci.gesture.models import GestureObservation


class StubEngine:
    def __init__(self) -> None:
        self.last_frame: MeaningFrame | None = None

    async def respond(self, frame: MeaningFrame) -> CharacterResponseV1:
        self.last_frame = frame
        return CharacterResponseV1.model_validate(
            {
                "schema_version": "rci.character_response.v1",
                "interaction_id": "interaction_1",
                "decision_id": "decision_1",
                "source_character": "aurelia",
                "speech": {
                    "text": "Hello.",
                    "delivery": "supportive",
                    "interruptible": True,
                },
                "expression": {"expression": "warm", "strength": "subtle"},
                "motion": {
                    "cue": "acknowledge",
                    "style": "restrained",
                    "disposition": "optional",
                },
                "verified": True,
                "persistence_committed": True,
                "persistence_durable": True,
            }
        )


@pytest.mark.asyncio
async def test_interaction_service_preserves_semantic_lineage_only() -> None:
    engine = StubEngine()
    service = InteractionService(engine)
    gesture = GestureObservation(
        GestureType.WAVE,
        0.8,
        1000,
        0.0,
        0.0,
        20.0,
        True,
    )
    result = await service.interact(timestamp_ms=1000, text="hello", gesture=gesture)

    assert engine.last_frame is not None
    assert engine.last_frame.gesture is GestureType.WAVE
    assert result.character_response.interaction_id == "interaction_1"
    assert result.behavior is not None
    assert result.behavior.decision_id == "decision_1"
    assert not hasattr(result.behavior, "joint_targets_deg")
    assert not hasattr(result.behavior, "pwm")
