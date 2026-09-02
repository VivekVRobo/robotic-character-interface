from pathlib import Path

import pytest

from rci.behavior import BehaviorIntent
from rci.characters.contracts import MotionCue, MotionStyle
from rci.protocols.constants import AckStatus, WireSystemState
from rci.robotics.model import RobotModel
from rci.robotics.profile import load_reference_profile
from rci.simulation.runtime import SimulationRuntime, SimulationRuntimeError

ROOT = Path(__file__).resolve().parents[3]


def _runtime() -> SimulationRuntime:
    model = RobotModel(
        load_reference_profile(ROOT / "configs" / "simulation" / "reference_arm.yaml")
    )
    return SimulationRuntime(model)


def _intent(cue: MotionCue = MotionCue.PRESENT) -> BehaviorIntent:
    return BehaviorIntent(
        interaction_id="interaction",
        decision_id="decision",
        source_character="aurelia",
        expression="confident",
        cue=cue,
        style=MotionStyle.RESTRAINED,
    )


@pytest.mark.asyncio
async def test_behavior_executes_through_gateway_into_digital_twin() -> None:
    runtime = _runtime()
    try:
        report = await runtime.execute_behavior(_intent())
        assert report.heartbeat_ack is AckStatus.OK
        assert report.motion_ack is AckStatus.OK
        assert report.simulation_only is True
        assert report.physical_motion is False
        assert report.simulation_steps > 0
        assert report.telemetry.state is WireSystemState.IDLE
        assert len(report.telemetry.joints) == 4
        assert all(runtime.model.within_limits(runtime.twin.state.positions_deg) for _ in (0,))
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_estop_blocks_behavior_until_explicit_reset() -> None:
    runtime = _runtime()
    try:
        receipt = await runtime.estop()
        assert receipt.ack_status is AckStatus.OK
        assert runtime.telemetry().state is WireSystemState.ESTOP

        with pytest.raises(SimulationRuntimeError, match="safety rejected"):
            await runtime.execute_behavior(_intent(MotionCue.THINK))

        assert runtime.reset_estop() is True
        report = await runtime.execute_behavior(_intent(MotionCue.THINK))
        assert report.motion_ack is AckStatus.OK
        assert report.telemetry.state is WireSystemState.IDLE
    finally:
        await runtime.close()
