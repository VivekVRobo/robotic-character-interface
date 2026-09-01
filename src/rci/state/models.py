"""Immutable state snapshots for the complete application runtime."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from rci.domain.enums import CharacterName, GestureType, RobotMode, SystemState, VoiceState
from rci.domain.timestamps import utc_now


class FrozenSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)


class SystemSnapshot(FrozenSnapshot):
    state: SystemState = SystemState.BOOT
    sequence: int = Field(default=0, ge=0)
    reason: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class RobotSnapshot(FrozenSnapshot):
    mode: RobotMode = RobotMode.DISABLED
    connected: bool = False
    joint_positions_deg: dict[str, float] = Field(default_factory=dict)
    active_trajectory_id: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class GestureSnapshot(FrozenSnapshot):
    connected: bool = False
    latest_gesture: GestureType = GestureType.UNKNOWN
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    updated_at: datetime = Field(default_factory=utc_now)


class VoiceSnapshot(FrozenSnapshot):
    state: VoiceState = VoiceState.IDLE
    latest_transcript: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class CharacterSnapshot(FrozenSnapshot):
    active_character: CharacterName | None = None
    emotion: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class SafetySnapshot(FrozenSnapshot):
    estop_active: bool = False
    motion_authorized: bool = False
    violation_count: int = Field(default=0, ge=0)
    latest_violation: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class StateSnapshot(FrozenSnapshot):
    revision: int = Field(default=0, ge=0)
    captured_at: datetime = Field(default_factory=utc_now)
    system: SystemSnapshot = Field(default_factory=SystemSnapshot)
    robot: RobotSnapshot = Field(default_factory=RobotSnapshot)
    gesture: GestureSnapshot = Field(default_factory=GestureSnapshot)
    voice: VoiceSnapshot = Field(default_factory=VoiceSnapshot)
    character: CharacterSnapshot = Field(default_factory=CharacterSnapshot)
    safety: SafetySnapshot = Field(default_factory=SafetySnapshot)
