"""FastAPI application for high-level software-only RCI interactions."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from rci.characters.client import CharacterEngine, CharacterEngineError
from rci.cognition.interaction_service import InteractionResult, InteractionService
from rci.domain.enums import GestureType
from rci.gesture.models import GestureObservation
from rci.protocols.messages import RobotTelemetry
from rci.simulation.runtime import (
    SimulationExecutionReport,
    SimulationRuntime,
    SimulationRuntimeError,
)
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


def create_api_app(
    character_engine: CharacterEngine,
    *,
    simulation_runtime: SimulationRuntime | None = None,
) -> FastAPI:
    """Create an API that cannot directly emit actuator or joint commands."""
    service = InteractionService(character_engine)
    app = FastAPI(title="Robotic Character Interface", version="0.1.0-dev0")

    @app.get("/api/status", response_model=StatusResponse)
    async def status() -> StatusResponse:
        return StatusResponse()

    @app.get("/api/dashboard/snapshot")
    async def dashboard_snapshot() -> dict[str, object]:
        runtime = _require_runtime(simulation_runtime)
        return await _serialize_dashboard_snapshot(runtime)

    @app.get("/api/simulation/telemetry")
    async def simulation_telemetry() -> dict[str, object]:
        runtime = _require_runtime(simulation_runtime)
        return _serialize_robot_telemetry(runtime.telemetry())

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
            execution = None
            if result.behavior is not None and simulation_runtime is not None:
                execution = await simulation_runtime.execute_behavior(result.behavior)
        except (CharacterEngineError, SimulationRuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return _serialize_result(result, execution)

    @app.post("/api/simulation/estop")
    async def simulation_estop() -> dict[str, object]:
        runtime = _require_runtime(simulation_runtime)
        receipt = await runtime.estop()
        return {
            "ack_status": receipt.ack_status.name,
            "physical_motion": False,
            "simulation_only": True,
        }

    @app.post("/api/simulation/reset-estop")
    async def simulation_reset_estop() -> dict[str, object]:
        runtime = _require_runtime(simulation_runtime)
        cleared = runtime.reset_estop()
        return {
            "cleared": cleared,
            "physical_motion": False,
            "simulation_only": True,
        }

    @app.websocket("/ws/telemetry")
    async def telemetry_websocket(websocket: WebSocket) -> None:
        runtime = _require_runtime(simulation_runtime)
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(
                    {
                        "dashboard": await _serialize_dashboard_snapshot(runtime),
                        "robotTelemetry": _serialize_robot_telemetry(runtime.telemetry()),
                    }
                )
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            return

    return app


def _require_runtime(runtime: SimulationRuntime | None) -> SimulationRuntime:
    if runtime is None:
        raise HTTPException(status_code=503, detail="digital twin runtime is unavailable")
    return runtime


def _serialize_result(
    result: InteractionResult,
    execution: SimulationExecutionReport | None = None,
) -> dict[str, object]:
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
        "simulation_execution": None if execution is None else _serialize_execution(execution),
    }


def _serialize_execution(report: SimulationExecutionReport) -> dict[str, object]:
    return {
        "cue": report.cue,
        "style": report.style,
        "safety_decision": report.safety_decision.value,
        "authorization_id": str(report.authorization_id),
        "heartbeat_ack": report.heartbeat_ack.name,
        "motion_ack": report.motion_ack.name,
        "simulation_steps": report.simulation_steps,
        "simulated_duration_s": report.simulated_duration_s,
        "telemetry": _serialize_robot_telemetry(report.telemetry),
        "simulation_only": report.simulation_only,
        "physical_motion": report.physical_motion,
    }


def _serialize_robot_telemetry(telemetry: RobotTelemetry) -> dict[str, object]:
    return {
        "uptimeMs": telemetry.uptime_ms,
        "systemState": telemetry.state.name,
        "flags": telemetry.flags,
        "supplyMv": telemetry.supply_mv,
        "joints": [
            {
                "jointId": joint.joint_id,
                "positionCdeg": joint.position_cdeg,
                "velocityCdegS": joint.velocity_cdeg_s,
                "currentMa": joint.current_ma,
            }
            for joint in telemetry.joints
        ],
        "simulationOnly": True,
        "measuredHardware": False,
    }


async def _serialize_dashboard_snapshot(runtime: SimulationRuntime) -> dict[str, object]:
    diagnostics = await runtime.diagnostics()
    return {
        "connection": "connected" if diagnostics.connected else "disconnected",
        "systemState": diagnostics.system_state.name,
        "estopLatched": diagnostics.estop_latched,
        "heartbeatHealthy": diagnostics.heartbeat_healthy,
        "gatewayError": None,
        "telemetry": {
            "lastFrameSequence": diagnostics.last_acknowledged_sequence,
            "heartbeatAgeMs": 0 if diagnostics.heartbeat_healthy else None,
            "sentCount": diagnostics.sent_count,
            "acknowledgedCount": diagnostics.acknowledged_count,
            "rejectedCount": diagnostics.rejected_count,
        },
    }
