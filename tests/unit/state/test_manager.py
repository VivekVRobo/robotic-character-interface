import pytest

from rci.domain.enums import RobotMode, SystemState
from rci.events.base import EventBusNotRunning
from rci.events.bus import EventBus
from rci.events.types import SystemStateChanged
from rci.state.manager import StateManager
from rci.state.models import RobotSnapshot
from rci.state.transitions import InvalidStateTransition


@pytest.mark.asyncio
async def test_nominal_state_path_updates_sequence_and_revision() -> None:
    bus = EventBus()
    manager = StateManager(bus)
    await bus.start()

    await manager.transition_system(SystemState.SELF_TEST)
    await manager.transition_system(SystemState.CALIBRATING)
    await manager.transition_system(SystemState.IDLE)
    await manager.transition_system(SystemState.ARMED)
    await manager.transition_system(SystemState.EXECUTING)
    await bus.join()
    await bus.stop()

    snapshot = manager.snapshot()
    assert snapshot.system.state is SystemState.EXECUTING
    assert snapshot.system.sequence == 5
    assert snapshot.revision == 5


@pytest.mark.asyncio
async def test_illegal_transition_does_not_modify_state() -> None:
    bus = EventBus()
    manager = StateManager(bus)
    await bus.start()

    with pytest.raises(InvalidStateTransition):
        await manager.transition_system(SystemState.ARMED)

    await bus.stop()
    assert manager.snapshot().system.state is SystemState.BOOT
    assert manager.snapshot().revision == 0


@pytest.mark.asyncio
async def test_transition_publishes_previous_and_current_state() -> None:
    bus = EventBus()
    manager = StateManager(bus)
    received: list[SystemStateChanged] = []

    async def handler(event: SystemStateChanged) -> None:
        received.append(event)

    bus.subscribe(SystemStateChanged, handler)
    await bus.start()
    await manager.transition_system(SystemState.SELF_TEST, reason="startup")
    await bus.join()
    await bus.stop()

    assert len(received) == 1
    assert received[0].previous_state is SystemState.BOOT
    assert received[0].current_state is SystemState.SELF_TEST
    assert received[0].reason == "startup"


@pytest.mark.asyncio
async def test_failed_event_publication_rolls_back_transition() -> None:
    bus = EventBus()
    manager = StateManager(bus)

    with pytest.raises(EventBusNotRunning):
        await manager.transition_system(SystemState.SELF_TEST)

    assert manager.snapshot().system.state is SystemState.BOOT
    assert manager.snapshot().revision == 0


@pytest.mark.asyncio
async def test_component_updates_are_atomic_revisioned_snapshots() -> None:
    bus = EventBus()
    manager = StateManager(bus)

    updated = await manager.update_robot(RobotSnapshot(mode=RobotMode.READY, connected=True))

    assert updated.revision == 1
    assert updated.robot.mode is RobotMode.READY
    assert updated.robot.connected is True
    assert manager.snapshot() == updated
