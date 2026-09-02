"""FastAPI application for high-level software-only RCI interactions."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from rci.characters.client import CharacterEngine, CharacterEngineError
from rci.cognition.interaction_service import InteractionResult, InteractionService
from rci.domain.enums import GestureType
from rci.gesture.models import GestureObservation
from rci.voice.models import VoiceTranscript


class SimulationInteractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation: Literal[True] = True
    timestamp_ms: int = Field(ge=0)
    text: str | None = None
    voice_text: str | None = None
    voice_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    gesture: GestureType | None = None
    gesture_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class StatusResponse(BaseModel):
    software_mode: Literal["simulation"] = "simulation"
    hardware_verified: Literal[False] = False
    physical_motion_enabled: Literal[False] = False
    character_engine: Literal["external"] = "external"


def create_api_app(character_engine: CharacterEngine) -> FastAPI:
    """Create an API that cannot directly emit actuator or joint commands."""
    service = InteractionService(character_engine)
    app = FastAPI(title="Robotic Character Interface", version="0.1.0-dev0")

    @app.get("/api/status", response_model=StatusResponse)
    async def status() -> StatusResponse:
        return StatusResponse()

    @app.post("/api/simulation/interact")
    async def interact(request: SimulationInteractionRequest) -> dict[str, object]:
        if request.text is not None and request.voice_text is not None:
            raise HTTPException(status_code=422, detail="provide text or simulated voice, not both")

        voice = None
        if request.voice_text is not None:
            normalized = " ".join(request.voice_text.split())
            if not normalized:
                raise HTTPException(status_code=422, detail="simulated voice text cannot be empty")
            voice = VoiceTranscript(normalized, request.voice_confidence, True)

        gesture = None
        if request.gesture is not None:
            gesture = GestureObservation(
                gesture=request.gesture,
                confidence=request.gesture_confidence,
                timestamp_ms=request.timestamp_ms,
                pitch_deg=0.0,
                roll_deg=0.0,
                angular_speed_deg_s=0.0,
                simulation=True,
            )

        try:
            result = await service.interact(
                timestamp_ms=request.timestamp_ms,
                text=request.text,
                voice=voice,
                gesture=gesture,
            )
        except (CharacterEngineError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return _serialize_result(result)

    return app


def _serialize_result(result: InteractionResult) -> dict[str, object]:
    behavior: dict[str, object] | None = None
    if result.behavior is not None:
        behavior = {
            "interaction_id": result.behavior.interaction_id,
            "decision_id": result.behavior.decision_id,
            "source_character": result.behavior.source_character,
            "expression": result.behavior.expression,
            "cue": result.behavior.cue.value,
            "style": result.behavior.style.value,
        }
    return {
        "meaning": {
            "text": result.meaning.text,
            "mode": result.meaning.mode.value,
            "timestamp_ms": result.meaning.timestamp_ms,
            "confidence": result.meaning.confidence,
            "gesture": None if result.meaning.gesture is None else result.meaning.gesture.value,
            "simulation": result.meaning.simulation,
        },
        "character_response": result.character_response.model_dump(mode="json"),
        "behavior": behavior,
        "actuator_command_emitted": False,
    }
