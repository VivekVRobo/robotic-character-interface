"""Typed runtime events that do not depend on future subsystem models."""

from typing import Literal

from pydantic import Field

from rci.domain.enums import FaultSeverity, GestureType, HealthStatus, SystemState
from rci.events.base import Event


class SystemStarted(Event):
    event_type: Literal["system.started"] = "system.started"
    version: str = Field(min_length=1)


class SystemStateChanged(Event):
    event_type: Literal["system.state_changed"] = "system.state_changed"
    previous_state: SystemState
    current_state: SystemState
    reason: str | None = None


class HealthChanged(Event):
    event_type: Literal["health.changed"] = "health.changed"
    component: str = Field(min_length=1)
    previous_status: HealthStatus
    current_status: HealthStatus
    detail: str | None = None


class GestureDetected(Event):
    event_type: Literal["gesture.detected"] = "gesture.detected"
    gesture: GestureType
    confidence: float = Field(ge=0.0, le=1.0)


class CharacterActivated(Event):
    event_type: Literal["character.activated"] = "character.activated"
    character_id: str = Field(min_length=1)


class TrajectoryRejected(Event):
    event_type: Literal["trajectory.rejected"] = "trajectory.rejected"
    trajectory_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class EmergencyStopTriggered(Event):
    event_type: Literal["safety.estop_triggered"] = "safety.estop_triggered"
    reason: str = Field(min_length=1)


class FaultDetected(Event):
    event_type: Literal["fault.detected"] = "fault.detected"
    component: str = Field(min_length=1)
    severity: FaultSeverity
    reason: str = Field(min_length=1)
