"""Strict consumer contract for verified character responses entering RCI."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Mapping, Self

from pydantic import BaseModel, ConfigDict, model_validator

SCHEMA_VERSION = "rci.character_response.v1"


class SpeechDelivery(StrEnum):
    NEUTRAL = "neutral"
    SUPPORTIVE = "supportive"
    CONFIDENT = "confident"
    CAUTIOUS = "cautious"
    ENCOURAGING = "encouraging"
    EMPATHETIC = "empathetic"


class ExpressionStrength(StrEnum):
    NONE = "none"
    SUBTLE = "subtle"
    MODERATE = "moderate"
    STRONG = "strong"


class MotionCue(StrEnum):
    NONE = "none"
    LISTEN = "listen"
    ACKNOWLEDGE = "acknowledge"
    PRESENT = "present"
    CAUTION = "caution"
    CELEBRATE = "celebrate"
    THINK = "think"


class MotionStyle(StrEnum):
    RESTRAINED = "restrained"
    STANDARD = "standard"
    EXPRESSIVE = "expressive"


class MotionDisposition(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"


class StrictContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SpeechIntent(StrictContractModel):
    text: str
    delivery: SpeechDelivery
    interruptible: bool

    @model_validator(mode="after")
    def validate_text(self) -> Self:
        if not self.text.strip():
            raise ValueError("speech text must not be empty")
        return self


class ExpressionIntent(StrictContractModel):
    expression: str
    strength: ExpressionStrength

    @model_validator(mode="after")
    def validate_expression(self) -> Self:
        if not self.expression.strip():
            raise ValueError("expression must not be empty")
        return self


class MotionIntent(StrictContractModel):
    cue: MotionCue
    style: MotionStyle
    disposition: MotionDisposition

    @model_validator(mode="after")
    def validate_disposition(self) -> Self:
        if self.cue == MotionCue.NONE and self.disposition != MotionDisposition.NONE:
            raise ValueError("a none motion cue must have none disposition")
        if self.cue != MotionCue.NONE and self.disposition != MotionDisposition.OPTIONAL:
            raise ValueError("non-empty character motion cues must remain optional")
        return self


class CharacterResponseV1(StrictContractModel):
    schema_version: Literal["rci.character_response.v1"]
    interaction_id: str
    decision_id: str
    source_character: Literal["aurelia"]
    speech: SpeechIntent
    expression: ExpressionIntent
    motion: MotionIntent
    verified: Literal[True]
    persistence_committed: Literal[True]
    persistence_durable: bool

    @model_validator(mode="after")
    def validate_identifiers(self) -> Self:
        if not self.interaction_id.strip() or not self.decision_id.strip():
            raise ValueError("interaction and decision identifiers must not be empty")
        return self


def parse_character_response(payload: Mapping[str, object]) -> CharacterResponseV1:
    """Validate a character payload before it reaches behavior planning."""
    return CharacterResponseV1.model_validate(payload)
