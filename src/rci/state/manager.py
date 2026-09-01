"""Concurrency-safe authoritative state manager."""

from __future__ import annotations

import asyncio

from rci.domain.enums import SystemState
from rci.domain.timestamps import utc_now
from rci.events.base import EventPriority
from rci.events.bus import EventBus
from rci.events.types import SystemStateChanged
from rci.state.models import (
    CharacterSnapshot,
    GestureSnapshot,
    RobotSnapshot,
    SafetySnapshot,
    StateSnapshot,
    SystemSnapshot,
    VoiceSnapshot,
)
from rci.state.transitions import validate_transition


class StateManager:
    """Own the immutable application snapshot and legal system transitions."""

    def __init__(self, event_bus: EventBus, initial: StateSnapshot | None = None) -> None:
        self._event_bus = event_bus
        self._snapshot = StateSnapshot() if initial is None else initial
        self._lock = asyncio.Lock()

    def snapshot(self) -> StateSnapshot:
        """Return the current immutable snapshot reference."""
        return self._snapshot

    async def transition_system(
        self,
        target: SystemState,
        *,
        reason: str | None = None,
        source: str = "state-manager",
    ) -> SystemSnapshot:
        """Apply one legal transition and publish its event transactionally."""
        async with self._lock:
            previous_snapshot = self._snapshot
            current = previous_snapshot.system
            validate_transition(current.state, target)

            updated = SystemSnapshot(
                state=target,
                sequence=current.sequence + 1,
                reason=reason,
                updated_at=utc_now(),
            )
            self._snapshot = previous_snapshot.model_copy(
                update={
                    "system": updated,
                    "revision": previous_snapshot.revision + 1,
                    "captured_at": utc_now(),
                }
            )

            priority = (
                EventPriority.CRITICAL
                if target in {SystemState.FAULT, SystemState.ESTOP}
                else EventPriority.HIGH
            )
            event = SystemStateChanged(
                source=source,
                previous_state=current.state,
                current_state=target,
                reason=reason,
            )
            try:
                await self._event_bus.publish(event, priority=priority)
            except Exception:
                self._snapshot = previous_snapshot
                raise

            return updated

    async def update_robot(self, value: RobotSnapshot) -> StateSnapshot:
        return await self._replace_component("robot", value)

    async def update_gesture(self, value: GestureSnapshot) -> StateSnapshot:
        return await self._replace_component("gesture", value)

    async def update_voice(self, value: VoiceSnapshot) -> StateSnapshot:
        return await self._replace_component("voice", value)

    async def update_character(self, value: CharacterSnapshot) -> StateSnapshot:
        return await self._replace_component("character", value)

    async def update_safety(self, value: SafetySnapshot) -> StateSnapshot:
        return await self._replace_component("safety", value)

    async def _replace_component(self, name: str, value: object) -> StateSnapshot:
        async with self._lock:
            current = self._snapshot
            self._snapshot = current.model_copy(
                update={name: value, "revision": current.revision + 1, "captured_at": utc_now()}
            )
            return self._snapshot
