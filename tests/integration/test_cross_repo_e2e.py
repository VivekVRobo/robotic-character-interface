from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from aurelia.llm.ollama_cortex import LocalOllamaCortex
from aurelia.runtime.api_contract import serialize_cognitive_cycle
from aurelia.runtime.cognitive_runtime import AureliaCognitiveRuntime

from rci.behavior import BehaviorIntent, BehaviorPlanner
from rci.characters.contracts import MotionCue, parse_character_response
from rci.domain.enums import SystemState
from rci.hardware.robot_gateway import RobotGateway
from rci.protocols.constants import AckStatus, MessageType, WireSystemState
from rci.safety.lifecycle import SafetyLifecycleController, SafetyLifecyclePolicy
from rci.safety.models import (
    CartesianPoint,
    JointConstraint,
    MotionCandidate,
    MotionDynamics,
    MotionSafetyPolicy,
    SafetyEnvelope,
    WorkspaceBounds,
)
from rci.safety.supervisor import MotionSafetySupervisor
from rci.simulation.protocol_link import SimulatedProtocolLink

from .firmware_bridge import (
    CompiledFirmwareBridge,
    FirmwareDispatch,
    serve_one_firmware_exchange,
)


def _simulation_motion_from_behavior(
    intent: BehaviorIntent,
) -> tuple[MotionCandidate, MotionDynamics]:
    """Map semantic behavior into a test-only pose; never used as a production planner."""
    if intent.cue is not MotionCue.PRESENT:
        raise ValueError(f"V004 simulation profile has no pose for cue {intent.cue.value!r}")
    return (
        MotionCandidate(
            system_state=SystemState.ARMED,
            estop_active=False,
            joint_targets_deg={"base": 10.0},
            workspace_point_mm=CartesianPoint(100.0, 0.0, 120.0),
        ),
        MotionDynamics(
            command_age_ms=0.0,
            heartbeat_age_ms=10.0,
            joint_velocities_deg_s={"base": 5.0},
            joint_accelerations_deg_s2={"base": 20.0},
        ),
    )


def _simulation_supervisor() -> MotionSafetySupervisor:
    """Create an explicitly synthetic verified envelope for software-only validation."""
    envelope = SafetyEnvelope(
        joints={
            "base": JointConstraint(
                name="base",
                min_deg=-90.0,
                max_deg=90.0,
                neutral_deg=0.0,
                verified=True,
            )
        },
        workspace=WorkspaceBounds(
            min_x_mm=-500.0,
            max_x_mm=500.0,
            min_y_mm=-500.0,
            max_y_mm=500.0,
            min_z_mm=0.0,
            max_z_mm=500.0,
            verified=True,
        ),
        allowed_states=frozenset({SystemState.ARMED}),
        robot_verified=True,
        servos_verified=True,
        motion_policy=MotionSafetyPolicy(
            command_ttl_ms=250.0,
            heartbeat_timeout_ms=500.0,
            max_velocity_deg_s=60.0,
            max_acceleration_deg_s2=180.0,
        ),
    )
    lifecycle = SafetyLifecycleController(SafetyLifecyclePolicy(heartbeat_timeout_ms=500.0))
    supervisor = MotionSafetySupervisor(envelope, lifecycle)
    supervisor.arm_watchdog()
    return supervisor


@pytest.mark.asyncio
async def test_real_aurelia_to_compiled_robot_runtime_e2e() -> None:
    bridge_path = os.environ.get("RCI_ROBOT_RUNTIME_BRIDGE")
    assert bridge_path, "RCI_ROBOT_RUNTIME_BRIDGE must point to the compiled C++ runtime bridge"

    with patch.object(LocalOllamaCortex, "query_local_model", return_value=None):
        cycle = AureliaCognitiveRuntime().process_query(
            "I received an offer with base $220k, 20% bonus, and $60k equity."
        )
    serialized = serialize_cognitive_cycle(cycle)
    raw_character = cast(Mapping[str, object], serialized["character_response"])

    character = parse_character_response(raw_character)
    assert character.decision_id == serialized["decision_id"]
    assert character.speech.text == serialized["response"]
    assert character.motion.cue is MotionCue.PRESENT

    behavior = BehaviorPlanner().plan(character)
    assert behavior is not None
    assert behavior.interaction_id == character.interaction_id
    assert behavior.decision_id == character.decision_id
    assert behavior.cue is MotionCue.PRESENT

    candidate, dynamics = _simulation_motion_from_behavior(behavior)
    supervisor = _simulation_supervisor()
    safety = supervisor.evaluate(candidate, dynamics)
    assert safety.approved
    assert safety.authorization is not None

    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=1.0)
    bridge = CompiledFirmwareBridge(Path(bridge_path))
    await bridge.open()

    try:
        heartbeat_exchange_task = asyncio.create_task(
            serve_one_firmware_exchange(link, bridge, now_ms=100)
        )
        heartbeat_receipt = await gateway.send_heartbeat(
            uptime_ms=100,
            state=WireSystemState.ARMED,
        )
        heartbeat_exchange = await heartbeat_exchange_task

        assert heartbeat_receipt.ack_status is AckStatus.OK
        assert heartbeat_exchange.request.message_type is MessageType.HEARTBEAT
        assert heartbeat_exchange.reply.dispatch is FirmwareDispatch.HEARTBEAT_ACCEPTED

        motion_exchange_task = asyncio.create_task(
            serve_one_firmware_exchange(link, bridge, now_ms=110)
        )
        motion_receipt = await gateway.send_authorization(safety.authorization)
        motion_exchange = await motion_exchange_task

        assert motion_receipt.ack_status is AckStatus.OK
        assert motion_receipt.authorization_id == safety.authorization.authorization_id
        assert motion_exchange.request.message_type is MessageType.VALIDATED_MOTION_COMMAND
        assert motion_exchange.reply.dispatch is FirmwareDispatch.MOTION_DEFERRED
        assert gateway.snapshot().acknowledged_count == 2
        assert gateway.snapshot().rejected_count == 0
    finally:
        await bridge.close()
        await link.close()
