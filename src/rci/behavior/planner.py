"""Deterministic semantic behavior planning for verified character responses."""

from __future__ import annotations

from dataclasses import dataclass

from rci.characters.contracts import (
    CharacterResponseV1,
    MotionCue,
    MotionDisposition,
    MotionStyle,
)


@dataclass(frozen=True, slots=True)
class BehaviorIntent:
    """Actuator-free behavior request emitted by the semantic planner."""

    interaction_id: str
    decision_id: str
    source_character: str
    expression: str
    cue: MotionCue
    style: MotionStyle


class BehaviorPlanner:
    """Translate verified character semantics into optional behavior intent only."""

    def plan(self, response: CharacterResponseV1) -> BehaviorIntent | None:
        """Return an actuator-free behavior intent or no physical behavior request."""
        motion = response.motion
        if motion.disposition is MotionDisposition.NONE:
            if motion.cue is not MotionCue.NONE:
                raise ValueError("none motion disposition cannot carry a non-empty cue")
            return None

        if motion.disposition is not MotionDisposition.OPTIONAL:
            raise ValueError("character behavior must remain optional")
        if motion.cue is MotionCue.NONE:
            raise ValueError("optional behavior must carry a semantic cue")

        return BehaviorIntent(
            interaction_id=response.interaction_id,
            decision_id=response.decision_id,
            source_character=response.source_character,
            expression=response.expression.expression,
            cue=motion.cue,
            style=motion.style,
        )
