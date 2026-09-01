from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from aurelia.llm.ollama_cortex import LocalOllamaCortex
from aurelia.runtime.api_contract import serialize_cognitive_cycle
from aurelia.runtime.cognitive_runtime import AureliaCognitiveRuntime
from pydantic import ValidationError

from rci.behavior import BehaviorIntent, BehaviorPlanner
from rci.characters.contracts import MotionCue, parse_character_response
from rci.domain.enums import MotionDecision, SystemState
from rci.hardware.robot_gateway import (
    RobotGateway,
    RobotGatewayError,
    RobotGatewayProtocolError,
    RobotGatewayRejected,
)
from rci.protocols.constants import AckStatus, EstopReason, MessageType, WireSystemState
from rci.protocols.framing import Frame
from rci.protocols.messages import Acknowledgement
from rci.safety.lifecycle import SafetyLifecycleController, SafetyLifecyclePolicy
from rci.safety.models import (
    CartesianPoint,
    JointConstraint,
    MotionCandidate,
    MotionDynamics,
    MotionSafetyPolicy,
    SafetyEnvelope,
    SafetyViolationCode,
    WorkspaceBounds,
)
from rci.safety.supervisor import MotionAuthorization, MotionSafetySupervisor
from rci.simulation.protocol_link import SimulatedProtocolLink

from .firmware_bridge import (
    CompiledFirmwareBridge,
    FirmwareDispatch,
    serve_one_firmware_exchange,
)


@pytest.fixture(scope="module")
def real_character_payload() -> dict[str, object]:
    """Produce one real Aurelia embodiment payload for the adversarial campaign."""
    with patch.object(LocalOllamaCortex, "query_local_model", return_value=None):
        cycle = AureliaCognitiveRuntime().process_query(
            "I received an offer with base $220k, 20% bonus, and $60k equity."
        )
    serialized = serialize_cognitive_cycle(cycle)
    return deepcopy(cast(dict[str, object], serialized["character_response"]))


def _behavior_from_payload(payload: Mapping[str, object]) -> BehaviorIntent:
    character = parse_character_response(payload)
    behavior = BehaviorPlanner().plan(character)
    assert behavior is not None
    assert behavior.cue is MotionCue.PRESENT
    return behavior


def _simulation_motion(
    behavior: BehaviorIntent,
) -> tuple[MotionCandidate, MotionDynamics]:
    if behavior.cue is not MotionCue.PRESENT:
        raise ValueError("V005 simulation profile only supports the verified present cue")
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


def _approved_authorization(payload: Mapping[str, object]) -> MotionAuthorization:
    behavior = _behavior_from_payload(payload)
    candidate, dynamics = _simulation_motion(behavior)
    supervisor = _simulation_supervisor()
    result = supervisor.evaluate(candidate, dynamics)
    assert result.approved
    assert result.authorization is not None
    return result.authorization


def _compiled_bridge_path() -> Path:
    value = os.environ.get("RCI_ROBOT_RUNTIME_BRIDGE")
    assert value, "RCI_ROBOT_RUNTIME_BRIDGE must point to the compiled C++ runtime bridge"
    return Path(value)


async def _send_firmware_heartbeat(
    gateway: RobotGateway,
    link: SimulatedProtocolLink,
    bridge: CompiledFirmwareBridge,
    *,
    now_ms: int,
) -> None:
    task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=now_ms))
    receipt = await gateway.send_heartbeat(uptime_ms=now_ms, state=WireSystemState.ARMED)
    exchange = await task
    assert receipt.ack_status is AckStatus.OK
    assert exchange.reply.dispatch is FirmwareDispatch.HEARTBEAT_ACCEPTED


async def _send_plain_ack(link: SimulatedProtocolLink) -> None:
    request = await link.device.receive_frame(timeout_s=1.0)
    acknowledgement = Acknowledgement(request.sequence, AckStatus.OK)
    await link.device.send_frame(
        Frame(MessageType.ACK, request.sequence, acknowledgement.encode())
    )


def test_unverified_aurelia_payload_is_rejected(
    real_character_payload: dict[str, object],
) -> None:
    tampered = deepcopy(real_character_payload)
    tampered["verified"] = False

    with pytest.raises(ValidationError):
        parse_character_response(tampered)


def test_malformed_aurelia_payload_is_rejected(
    real_character_payload: dict[str, object],
) -> None:
    tampered = deepcopy(real_character_payload)
    speech = cast(dict[str, object], tampered["speech"])
    del speech["text"]

    with pytest.raises(ValidationError):
        parse_character_response(tampered)


def test_actuator_field_injection_is_rejected(
    real_character_payload: dict[str, object],
) -> None:
    tampered = deepcopy(real_character_payload)
    motion = cast(dict[str, object], tampered["motion"])
    motion["servo"] = {"channel": 0, "pwm": 1500}

    with pytest.raises(ValidationError):
        parse_character_response(tampered)


def test_stale_command_is_rejected_before_authorization(
    real_character_payload: dict[str, object],
) -> None:
    behavior = _behavior_from_payload(real_character_payload)
    candidate, dynamics = _simulation_motion(behavior)
    supervisor = _simulation_supervisor()

    result = supervisor.evaluate(candidate, replace(dynamics, command_age_ms=251.0))

    assert result.decision is MotionDecision.REJECT
    assert result.authorization is None
    assert any(v.code is SafetyViolationCode.COMMAND_STALE for v in result.violations)


def test_stale_heartbeat_latches_and_requires_manual_reset(
    real_character_payload: dict[str, object],
) -> None:
    behavior = _behavior_from_payload(real_character_payload)
    candidate, dynamics = _simulation_motion(behavior)
    supervisor = _simulation_supervisor()

    stale = supervisor.evaluate(candidate, replace(dynamics, heartbeat_age_ms=501.0))
    assert stale.decision is MotionDecision.ESTOP
    assert stale.authorization is None
    assert stale.lifecycle.estop_latched

    fresh_but_latched = supervisor.evaluate(candidate, dynamics)
    assert fresh_but_latched.decision is MotionDecision.ESTOP
    assert fresh_but_latched.authorization is None

    reset = supervisor.request_manual_reset()
    assert reset.cleared

    recovered = supervisor.evaluate(candidate, dynamics)
    assert recovered.approved
    assert recovered.authorization is not None


@pytest.mark.asyncio
async def test_firmware_before_heartbeat_nacks_then_recovers(
    real_character_payload: dict[str, object],
) -> None:
    authorization = _approved_authorization(real_character_payload)
    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=1.0)
    bridge = CompiledFirmwareBridge(_compiled_bridge_path())
    await bridge.open()

    try:
        unsafe_task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=100))
        with pytest.raises(RobotGatewayRejected, match="REJECTED"):
            await gateway.send_authorization(authorization)
        unsafe_exchange = await unsafe_task
        assert unsafe_exchange.reply.dispatch is FirmwareDispatch.MOTION_REJECTED_UNSAFE
        assert unsafe_exchange.reply.ack_status is AckStatus.REJECTED

        await _send_firmware_heartbeat(gateway, link, bridge, now_ms=110)

        recovery_task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=120))
        receipt = await gateway.send_authorization(authorization)
        recovery_exchange = await recovery_task
        assert receipt.ack_status is AckStatus.OK
        assert recovery_exchange.reply.dispatch is FirmwareDispatch.MOTION_DEFERRED
    finally:
        await bridge.close()
        await link.close()


@pytest.mark.asyncio
async def test_estop_during_flow_blocks_previously_authorized_motion(
    real_character_payload: dict[str, object],
) -> None:
    authorization = _approved_authorization(real_character_payload)
    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=1.0)
    bridge = CompiledFirmwareBridge(_compiled_bridge_path())
    await bridge.open()

    try:
        await _send_firmware_heartbeat(gateway, link, bridge, now_ms=100)

        estop_task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=110))
        estop_receipt = await gateway.send_estop(EstopReason.SAFETY)
        estop_exchange = await estop_task
        assert estop_receipt.ack_status is AckStatus.OK
        assert estop_exchange.reply.dispatch is FirmwareDispatch.ESTOP_LATCHED

        blocked_task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=120))
        with pytest.raises(RobotGatewayRejected, match="REJECTED"):
            await gateway.send_authorization(authorization)
        blocked_exchange = await blocked_task
        assert blocked_exchange.reply.dispatch is FirmwareDispatch.MOTION_REJECTED_UNSAFE
    finally:
        await bridge.close()
        await link.close()


@pytest.mark.asyncio
async def test_duplicate_authorization_is_rejected_as_stale(
    real_character_payload: dict[str, object],
) -> None:
    authorization = _approved_authorization(real_character_payload)
    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=1.0)
    bridge = CompiledFirmwareBridge(_compiled_bridge_path())
    await bridge.open()

    try:
        await _send_firmware_heartbeat(gateway, link, bridge, now_ms=100)

        first_task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=110))
        first_receipt = await gateway.send_authorization(authorization)
        first_exchange = await first_task
        assert first_receipt.ack_status is AckStatus.OK
        assert first_exchange.reply.dispatch is FirmwareDispatch.MOTION_DEFERRED

        duplicate_task = asyncio.create_task(serve_one_firmware_exchange(link, bridge, now_ms=120))
        with pytest.raises(RobotGatewayRejected, match="STALE"):
            await gateway.send_authorization(authorization)
        duplicate_exchange = await duplicate_task
        assert duplicate_exchange.reply.dispatch is FirmwareDispatch.REJECTED_REPLAY
        assert duplicate_exchange.reply.ack_status is AckStatus.STALE
    finally:
        await bridge.close()
        await link.close()


@pytest.mark.asyncio
async def test_ack_timeout_fails_closed_and_next_request_can_recover() -> None:
    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=0.02)

    try:
        with pytest.raises(RobotGatewayError, match="acknowledgement failed"):
            await gateway.send_heartbeat(uptime_ms=100, state=WireSystemState.ARMED)

        timed_out_request = await link.device.receive_frame(timeout_s=1.0)
        assert timed_out_request.sequence == 0

        responder = asyncio.create_task(_send_plain_ack(link))
        receipt = await gateway.send_heartbeat(uptime_ms=110, state=WireSystemState.ARMED)
        await responder
        assert receipt.ack_status is AckStatus.OK
        assert receipt.frame_sequence == 1
    finally:
        await link.close()


@pytest.mark.asyncio
async def test_mismatched_ack_sequence_is_rejected() -> None:
    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=1.0)

    async def send_mismatched_ack() -> None:
        request = await link.device.receive_frame(timeout_s=1.0)
        wrong_sequence = (request.sequence + 1) & 0xFFFF
        acknowledgement = Acknowledgement(wrong_sequence, AckStatus.OK)
        await link.device.send_frame(
            Frame(MessageType.ACK, request.sequence, acknowledgement.encode())
        )

    try:
        responder = asyncio.create_task(send_mismatched_ack())
        with pytest.raises(RobotGatewayProtocolError, match="sequence does not match"):
            await gateway.send_heartbeat(uptime_ms=100, state=WireSystemState.ARMED)
        await responder
    finally:
        await link.close()


@pytest.mark.asyncio
async def test_corrupted_ack_is_visible_and_stream_recovers() -> None:
    link = await SimulatedProtocolLink.create(read_size=7)
    gateway = RobotGateway(link.host, {"base": 1}, ack_timeout_s=1.0)

    async def send_corrupted_ack() -> None:
        request = await link.device.receive_frame(timeout_s=1.0)
        acknowledgement = Acknowledgement(request.sequence, AckStatus.OK)
        raw = bytearray(Frame(MessageType.ACK, request.sequence, acknowledgement.encode()).encode())
        raw[-1] ^= 0x01
        await link.inject_to_host(bytes(raw))

    try:
        corrupt_responder = asyncio.create_task(send_corrupted_ack())
        with pytest.raises(RobotGatewayError, match="acknowledgement failed"):
            await gateway.send_heartbeat(uptime_ms=100, state=WireSystemState.ARMED)
        await corrupt_responder

        recovery_responder = asyncio.create_task(_send_plain_ack(link))
        recovered = await gateway.send_heartbeat(uptime_ms=110, state=WireSystemState.ARMED)
        await recovery_responder
        assert recovered.ack_status is AckStatus.OK
        assert recovered.frame_sequence == 1
    finally:
        await link.close()


@pytest.mark.asyncio
async def test_disconnect_is_normalized_and_new_link_recovers() -> None:
    broken_link = await SimulatedProtocolLink.create(read_size=7)
    broken_gateway = RobotGateway(broken_link.host, {"base": 1}, ack_timeout_s=0.1)
    await broken_link.device.close()

    try:
        with pytest.raises(RobotGatewayError, match="send failed"):
            await broken_gateway.send_heartbeat(uptime_ms=100, state=WireSystemState.ARMED)
    finally:
        await broken_link.close()

    recovered_link = await SimulatedProtocolLink.create(read_size=7)
    recovered_gateway = RobotGateway(recovered_link.host, {"base": 1}, ack_timeout_s=1.0)
    try:
        responder = asyncio.create_task(_send_plain_ack(recovered_link))
        receipt = await recovered_gateway.send_heartbeat(
            uptime_ms=110,
            state=WireSystemState.ARMED,
        )
        await responder
        assert receipt.ack_status is AckStatus.OK
    finally:
        await recovered_link.close()
