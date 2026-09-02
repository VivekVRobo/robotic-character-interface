from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rci.api import create_api_app
from rci.characters.contracts import CharacterResponseV1
from rci.cognition.meaning import MeaningFrame
from rci.robotics import RobotModel, load_reference_profile
from rci.simulation.runtime import SimulationRuntime

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "configs" / "simulation" / "reference_arm.yaml"


class MotionEngine:
    async def respond(self, frame: MeaningFrame) -> CharacterResponseV1:
        return CharacterResponseV1.model_validate(
            {
                "schema_version": "rci.character_response.v1",
                "interaction_id": "interaction_runtime",
                "decision_id": "decision_runtime",
                "source_character": "aurelia",
                "speech": {
                    "text": f"Received: {frame.text}",
                    "delivery": "confident",
                    "interruptible": True,
                },
                "expression": {"expression": "confident", "strength": "subtle"},
                "motion": {
                    "cue": "present",
                    "style": "restrained",
                    "disposition": "optional",
                },
                "verified": True,
                "persistence_committed": True,
                "persistence_durable": False,
            }
        )


def _runtime() -> SimulationRuntime:
    return SimulationRuntime(RobotModel(load_reference_profile(PROFILE)))


@pytest.mark.asyncio
async def test_interaction_executes_only_in_digital_twin_and_updates_dashboard() -> None:
    runtime = _runtime()
    app = create_api_app(MotionEngine(), simulation_runtime=runtime)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/simulation/interact",
                json={"simulation": True, "timestamp_ms": 1000, "text": "show me"},
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["actuator_command_emitted"] is False
            assert payload["simulation_execution"]["simulation_only"] is True
            assert payload["simulation_execution"]["physical_motion"] is False
            assert payload["simulation_execution"]["heartbeat_ack"] == "OK"
            assert payload["simulation_execution"]["motion_ack"] == "OK"

            snapshot = (await client.get("/api/dashboard/snapshot")).json()
            assert snapshot["connection"] == "connected"
            assert snapshot["gatewayError"] is None
            assert snapshot["telemetry"]["sentCount"] == 2
            assert snapshot["telemetry"]["acknowledgedCount"] == 2

            telemetry = (await client.get("/api/simulation/telemetry")).json()
            assert telemetry["simulationOnly"] is True
            assert telemetry["measuredHardware"] is False
            assert len(telemetry["joints"]) == 4
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_api_estop_requires_explicit_reset_before_motion_recovers() -> None:
    runtime = _runtime()
    app = create_api_app(MotionEngine(), simulation_runtime=runtime)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            estop = await client.post("/api/simulation/estop")
            assert estop.status_code == 200
            assert estop.json()["simulation_only"] is True

            blocked = await client.post(
                "/api/simulation/interact",
                json={"simulation": True, "timestamp_ms": 1001, "text": "move"},
            )
            assert blocked.status_code == 503

            reset = await client.post("/api/simulation/reset-estop")
            assert reset.status_code == 200
            assert reset.json()["cleared"] is True

            recovered = await client.post(
                "/api/simulation/interact",
                json={"simulation": True, "timestamp_ms": 1002, "text": "move"},
            )
            assert recovered.status_code == 200
            assert recovered.json()["simulation_execution"]["motion_ack"] == "OK"
    finally:
        await runtime.close()
