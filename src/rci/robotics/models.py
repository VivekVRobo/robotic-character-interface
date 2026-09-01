"""Typed simulation-only robot models and trajectory records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssumptionProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["engineering_prediction"]
    confidence: Literal["low", "medium", "high"]
    note: str = Field(min_length=1)


class ReferenceGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    base_height_mm: float = Field(gt=0)
    shoulder_link_mm: float = Field(gt=0)
    forearm_link_mm: float = Field(gt=0)
    tool_length_mm: float = Field(ge=0)


class ReferenceJoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    protocol_id: int = Field(ge=1, le=255)
    lower_deg: float
    upper_deg: float
    home_deg: float
    max_velocity_deg_s: float = Field(gt=0)
    max_acceleration_deg_s2: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> ReferenceJoint:
        if not self.lower_deg < self.home_deg < self.upper_deg:
            raise ValueError("joint must satisfy lower < home < upper")
        return self


class ReferenceRobotProfile(BaseModel):
    """Engineering-predicted robot definition that can never claim hardware verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["rci.reference_robot.v1"]
    profile_id: str = Field(min_length=1)
    simulation_only: Literal[True]
    hardware_verified: Literal[False]
    provenance: AssumptionProvenance
    geometry: ReferenceGeometry
    joints: dict[str, ReferenceJoint]

    @model_validator(mode="after")
    def validate_joint_set(self) -> ReferenceRobotProfile:
        required = {"base", "shoulder", "elbow", "gripper"}
        if set(self.joints) != required:
            raise ValueError(f"reference robot joints must be exactly {sorted(required)}")
        ids = [joint.protocol_id for joint in self.joints.values()]
        if len(ids) != len(set(ids)):
            raise ValueError("reference robot protocol IDs must be unique")
        return self


@dataclass(frozen=True, slots=True)
class CartesianPose:
    x_mm: float
    y_mm: float
    z_mm: float


@dataclass(frozen=True, slots=True)
class JointSolution:
    base_deg: float
    shoulder_deg: float
    elbow_deg: float
    gripper_deg: float

    def as_dict(self) -> dict[str, float]:
        return {
            "base": self.base_deg,
            "shoulder": self.shoulder_deg,
            "elbow": self.elbow_deg,
            "gripper": self.gripper_deg,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceEstimate:
    min_x_mm: float
    max_x_mm: float
    min_y_mm: float
    max_y_mm: float
    min_z_mm: float
    max_z_mm: float
    samples: int


@dataclass(frozen=True, slots=True)
class TrajectorySample:
    time_s: float
    positions_deg: dict[str, float]
    velocities_deg_s: dict[str, float]
    accelerations_deg_s2: dict[str, float]


@dataclass(frozen=True, slots=True)
class JointTrajectory:
    duration_s: float
    samples: tuple[TrajectorySample, ...]

    @property
    def start(self) -> TrajectorySample:
        return self.samples[0]

    @property
    def end(self) -> TrajectorySample:
        return self.samples[-1]
