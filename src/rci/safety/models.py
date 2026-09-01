"""Immutable deterministic safety models for motion eligibility."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

from rci.domain.enums import MotionDecision, SafetySeverity, SystemState


class SafetyViolationCode(StrEnum):
    """Machine-readable reason codes produced by deterministic safety checks."""

    ESTOP_ACTIVE = "ESTOP_ACTIVE"
    STATE_NOT_ALLOWED = "STATE_NOT_ALLOWED"
    JOINT_MODEL_UNVERIFIED = "JOINT_MODEL_UNVERIFIED"
    WORKSPACE_MODEL_UNVERIFIED = "WORKSPACE_MODEL_UNVERIFIED"
    EMPTY_JOINT_TARGETS = "EMPTY_JOINT_TARGETS"
    UNKNOWN_JOINT = "UNKNOWN_JOINT"
    INVALID_NUMERIC_TARGET = "INVALID_NUMERIC_TARGET"
    JOINT_LIMIT_VIOLATION = "JOINT_LIMIT_VIOLATION"
    WORKSPACE_TARGET_REQUIRED = "WORKSPACE_TARGET_REQUIRED"
    WORKSPACE_LIMIT_VIOLATION = "WORKSPACE_LIMIT_VIOLATION"
    MOTION_POLICY_UNAVAILABLE = "MOTION_POLICY_UNAVAILABLE"
    COMMAND_AGE_INVALID = "COMMAND_AGE_INVALID"
    COMMAND_STALE = "COMMAND_STALE"
    HEARTBEAT_AGE_INVALID = "HEARTBEAT_AGE_INVALID"
    HEARTBEAT_STALE = "HEARTBEAT_STALE"
    VELOCITY_SAMPLE_MISSING = "VELOCITY_SAMPLE_MISSING"
    ACCELERATION_SAMPLE_MISSING = "ACCELERATION_SAMPLE_MISSING"
    DYNAMIC_SAMPLE_UNKNOWN_JOINT = "DYNAMIC_SAMPLE_UNKNOWN_JOINT"
    VELOCITY_LIMIT_VIOLATION = "VELOCITY_LIMIT_VIOLATION"
    ACCELERATION_LIMIT_VIOLATION = "ACCELERATION_LIMIT_VIOLATION"


@dataclass(frozen=True, slots=True)
class JointConstraint:
    """Measured angular envelope for one physical joint."""

    name: str
    min_deg: float | None
    max_deg: float | None
    neutral_deg: float | None
    verified: bool = False

    @property
    def complete(self) -> bool:
        return (
            self.min_deg is not None and self.max_deg is not None and self.neutral_deg is not None
        )

    @property
    def verified_complete(self) -> bool:
        if not self.verified or not self.complete:
            return False
        assert self.min_deg is not None
        assert self.max_deg is not None
        assert self.neutral_deg is not None
        return self.min_deg < self.neutral_deg < self.max_deg

    def contains(self, angle_deg: float) -> bool:
        if not self.verified_complete or not isfinite(angle_deg):
            return False
        assert self.min_deg is not None and self.max_deg is not None
        return self.min_deg <= angle_deg <= self.max_deg


@dataclass(frozen=True, slots=True)
class CartesianPoint:
    """Cartesian point in robot-base coordinates."""

    x_mm: float
    y_mm: float
    z_mm: float

    @property
    def finite(self) -> bool:
        return isfinite(self.x_mm) and isfinite(self.y_mm) and isfinite(self.z_mm)


@dataclass(frozen=True, slots=True)
class WorkspaceBounds:
    """Measured axis-aligned physical workspace envelope."""

    min_x_mm: float | None
    max_x_mm: float | None
    min_y_mm: float | None
    max_y_mm: float | None
    min_z_mm: float | None
    max_z_mm: float | None
    verified: bool = False

    @property
    def complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.min_x_mm,
                self.max_x_mm,
                self.min_y_mm,
                self.max_y_mm,
                self.min_z_mm,
                self.max_z_mm,
            )
        )

    @property
    def verified_complete(self) -> bool:
        if not self.verified or not self.complete:
            return False
        assert self.min_x_mm is not None and self.max_x_mm is not None
        assert self.min_y_mm is not None and self.max_y_mm is not None
        assert self.min_z_mm is not None and self.max_z_mm is not None
        return (
            self.min_x_mm < self.max_x_mm
            and self.min_y_mm < self.max_y_mm
            and self.min_z_mm < self.max_z_mm
        )

    def contains(self, point: CartesianPoint) -> bool:
        if not self.verified_complete or not point.finite:
            return False
        assert self.min_x_mm is not None and self.max_x_mm is not None
        assert self.min_y_mm is not None and self.max_y_mm is not None
        assert self.min_z_mm is not None and self.max_z_mm is not None
        return (
            self.min_x_mm <= point.x_mm <= self.max_x_mm
            and self.min_y_mm <= point.y_mm <= self.max_y_mm
            and self.min_z_mm <= point.z_mm <= self.max_z_mm
        )


@dataclass(frozen=True, slots=True)
class MotionSafetyPolicy:
    """Configured dynamic limits and freshness thresholds."""

    command_ttl_ms: float
    heartbeat_timeout_ms: float
    max_velocity_deg_s: float
    max_acceleration_deg_s2: float

    @property
    def valid(self) -> bool:
        values = (
            self.command_ttl_ms,
            self.heartbeat_timeout_ms,
            self.max_velocity_deg_s,
            self.max_acceleration_deg_s2,
        )
        return all(isfinite(value) and value > 0 for value in values)


@dataclass(frozen=True, slots=True)
class SafetyEnvelope:
    """Configuration-derived physical safety envelope."""

    joints: Mapping[str, JointConstraint]
    workspace: WorkspaceBounds
    allowed_states: frozenset[SystemState]
    robot_verified: bool
    servos_verified: bool
    motion_policy: MotionSafetyPolicy | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "joints", MappingProxyType(dict(self.joints)))

    @property
    def physical_constraints_verified(self) -> bool:
        return (
            self.robot_verified
            and self.servos_verified
            and bool(self.joints)
            and all(joint.verified_complete for joint in self.joints.values())
            and self.workspace.verified_complete
        )


@dataclass(frozen=True, slots=True)
class MotionCandidate:
    """Candidate pose evaluated before dynamic trajectory checks."""

    system_state: SystemState
    estop_active: bool
    joint_targets_deg: Mapping[str, float]
    workspace_point_mm: CartesianPoint | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "joint_targets_deg",
            MappingProxyType(dict(self.joint_targets_deg)),
        )


@dataclass(frozen=True, slots=True)
class MotionDynamics:
    """Freshness and per-joint dynamic samples for one candidate command."""

    command_age_ms: float
    heartbeat_age_ms: float
    joint_velocities_deg_s: Mapping[str, float] = field(default_factory=dict)
    joint_accelerations_deg_s2: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "joint_velocities_deg_s",
            MappingProxyType(dict(self.joint_velocities_deg_s)),
        )
        object.__setattr__(
            self,
            "joint_accelerations_deg_s2",
            MappingProxyType(dict(self.joint_accelerations_deg_s2)),
        )


@dataclass(frozen=True, slots=True)
class SafetyViolation:
    """One deterministic reason motion cannot proceed."""

    code: SafetyViolationCode
    detail: str
    severity: SafetySeverity = SafetySeverity.CRITICAL


@dataclass(frozen=True, slots=True)
class MotionEligibility:
    """Fail-closed eligibility result consumed by later safety layers."""

    decision: MotionDecision
    violations: tuple[SafetyViolation, ...]

    @property
    def approved(self) -> bool:
        return self.decision is MotionDecision.APPROVE and not self.violations
