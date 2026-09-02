from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from aurelia.llm.ollama_cortex import LocalOllamaCortex
from aurelia.runtime.api_contract import serialize_cognitive_cycle
from aurelia.runtime.cognitive_runtime import AureliaCognitiveRuntime

from rci.behavior import BehaviorPlanner
from rci.characters.contracts import MotionCue, parse_character_response
from rci.protocols.constants import AckStatus, WireSystemState
from rci.robotics import RobotModel, load_reference_profile
from rci.simulation.runtime import SimulationRuntime

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "configs" / "simulation" / "reference_arm.yaml"


@pytest.mark.asyncio
async def test_real_aurelia_semantics_execute_through_final_digital_twin_runtime() -> None:
    with patch.object(LocalOllamaCortex, "query_local_model", return_value=None):
        cycle = AureliaCognitiveRuntime().process_query(
            "I received an offer with base $220k, 20% bonus, and $60k equity."
        )
    serialized = serialize_cognitive_cycle(cycle)
    raw_character = cast(Mapping[str, object], serialized["character_response"])
    character = parse_character_response(raw_character)

    assert character.verified is True
    assert character.persistence_committed is True
    assert character.motion.cue is MotionCue.PRESENT

    behavior = BehaviorPlanner().plan(character)
    assert behavior is not None
    assert behavior.interaction_id == character.interaction_id
    assert behavior.decision_id == character.decision_id

    runtime = SimulationRuntime(RobotModel(load_reference_profile(PROFILE)))
    try:
        report = await runtime.execute_behavior(behavior)
        diagnostics = await runtime.diagnostics()

        assert report.heartbeat_ack is AckStatus.OK
        assert report.motion_ack is AckStatus.OK
        assert report.simulation_only is True
        assert report.physical_motion is False
        assert report.telemetry.state is WireSystemState.IDLE
        assert len(report.telemetry.joints) == 4
        assert diagnostics.connected is True
        assert diagnostics.hardware_verified is False
        assert diagnostics.physical_motion_enabled is False
        assert diagnostics.rejected_count == 0
    finally:
        await runtime.close()
