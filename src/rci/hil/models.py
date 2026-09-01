"""Typed evidence, permit, and run-result models for the single-servo HIL gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HIL_EVIDENCE_SCHEMA_VERSION: Literal["rci.single_servo_hil_evidence.v1"] = (
    "rci.single_servo_hil_evidence.v1"
)
HIL_PERMIT_SCHEMA_VERSION: Literal["rci.single_servo_hil_permit.v1"] = (
    "rci.single_servo_hil_permit.v1"
)
HIL_RUN_RESULT_SCHEMA_VERSION: Literal["rci.single_servo_hil_run_result.v1"] = (
    "rci.single_servo_hil_run_result.v1"
)


class EvidenceKind(StrEnum):
    WIRING = "wiring"
    MEASUREMENT = "measurement"
    PHOTO = "photo"
    VIDEO = "video"
    TELEMETRY = "telemetry"


class HilRunOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    ABORTED = "aborted"


class EvidenceReference(BaseModel):
    """Content-addressed reference to one operator-supplied evidence artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvidenceKind
    uri: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ElectricalEvidence(BaseModel):
    """Measured electrical setup; no voltage/current values are assumed by software."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    actuator_supply_voltage_v: float = Field(gt=0)
    logic_supply_voltage_v: float = Field(gt=0)
    current_limit_a: float = Field(gt=0)
    common_ground_verified: bool = False
    actuator_logic_rails_separate: bool = False
    independent_estop_verified: bool = False
    power_cut_verified: bool = False


class MechanicalEvidence(BaseModel):
    """Operator checks required before even one servo may be energized."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    servo_secured: bool = False
    load_path_clear: bool = False
    manual_range_check_verified: bool = False
    hard_stop_clearance_verified: bool = False


class ServoCalibrationEvidence(BaseModel):
    """Measured angle/pulse mapping and deliberately narrower first-test envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    joint_name: str = Field(min_length=1)
    servo_model: str = Field(min_length=1)
    driver: str = Field(min_length=1)
    pwm_frequency_hz: float = Field(gt=0)
    channel: int = Field(ge=0, le=15)
    protocol_id: int = Field(ge=1, le=255)
    lower_angle_deg: float
    neutral_angle_deg: float
    upper_angle_deg: float
    lower_pulse_us: int = Field(gt=0)
    neutral_pulse_us: int = Field(gt=0)
    upper_pulse_us: int = Field(gt=0)
    test_lower_angle_deg: float
    test_upper_angle_deg: float
    max_test_step_deg: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_ranges(self) -> ServoCalibrationEvidence:
        if not self.lower_angle_deg < self.neutral_angle_deg < self.upper_angle_deg:
            raise ValueError("measured angles must satisfy lower < neutral < upper")
        if self.lower_pulse_us == self.upper_pulse_us:
            raise ValueError("measured pulse endpoints must be distinct")

        pulse_low = min(self.lower_pulse_us, self.upper_pulse_us)
        pulse_high = max(self.lower_pulse_us, self.upper_pulse_us)
        if not pulse_low < self.neutral_pulse_us < pulse_high:
            raise ValueError("neutral pulse must lie strictly between measured pulse endpoints")

        if not self.lower_angle_deg <= self.test_lower_angle_deg < self.test_upper_angle_deg:
            raise ValueError("test lower angle must lie inside the measured angle range")
        if not self.test_upper_angle_deg <= self.upper_angle_deg:
            raise ValueError("test upper angle must lie inside the measured angle range")
        if not self.test_lower_angle_deg <= self.neutral_angle_deg <= self.test_upper_angle_deg:
            raise ValueError("neutral angle must lie inside the first-test envelope")
        if self.max_test_step_deg > self.test_upper_angle_deg - self.test_lower_angle_deg:
            raise ValueError("max test step cannot exceed the first-test envelope width")
        return self


class SingleServoHilEvidence(BaseModel):
    """Complete operator evidence required before a single-servo permit can exist."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["rci.single_servo_hil_evidence.v1"] = HIL_EVIDENCE_SCHEMA_VERSION
    recorded_at: datetime
    operator: str = Field(min_length=1)
    calibration: ServoCalibrationEvidence
    electrical: ElectricalEvidence
    mechanical: MechanicalEvidence
    evidence_refs: tuple[EvidenceReference, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def require_artifact_classes(self) -> SingleServoHilEvidence:
        if self.recorded_at.tzinfo is None:
            raise ValueError("recorded_at must be timezone-aware")
        kinds = {reference.kind for reference in self.evidence_refs}
        if EvidenceKind.WIRING not in kinds:
            raise ValueError("HIL evidence must include a wiring artifact")
        if EvidenceKind.MEASUREMENT not in kinds:
            raise ValueError("HIL evidence must include a measurement artifact")
        return self


class HilActivationPermit(BaseModel):
    """Narrow, content-bound authorization to attempt one-servo HIL only."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    schema_version: Literal["rci.single_servo_hil_permit.v1"] = HIL_PERMIT_SCHEMA_VERSION
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    joint_name: str
    channel: int = Field(ge=0, le=15)
    protocol_id: int = Field(ge=1, le=255)
    lower_angle_deg: float
    neutral_angle_deg: float
    upper_angle_deg: float
    lower_pulse_us: int = Field(gt=0)
    neutral_pulse_us: int = Field(gt=0)
    upper_pulse_us: int = Field(gt=0)
    test_lower_angle_deg: float
    test_upper_angle_deg: float
    max_test_step_deg: float = Field(gt=0)


class HilTargetObservation(BaseModel):
    """One physical command/observation sample from a real single-servo run."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    commanded_angle_deg: float
    observed_angle_deg: float
    commanded_pulse_us: int = Field(gt=0)
    observed_current_a: float = Field(ge=0)


class SingleServoHilRunResult(BaseModel):
    """Post-run physical evidence; PASS has intentionally strict requirements."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    schema_version: Literal["rci.single_servo_hil_run_result.v1"] = HIL_RUN_RESULT_SCHEMA_VERSION
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    joint_name: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime
    outcome: HilRunOutcome
    observations: tuple[HilTargetObservation, ...] = ()
    estop_response_verified: bool = False
    power_cut_response_verified: bool = False
    unexpected_motion: bool = False
    operator_notes: str = ""
    evidence_refs: tuple[EvidenceReference, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> SingleServoHilRunResult:
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("run timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        if self.outcome is HilRunOutcome.PASS:
            if not self.observations:
                raise ValueError("PASS requires at least one physical observation")
            if self.unexpected_motion:
                raise ValueError("PASS cannot include unexpected motion")
            if not self.estop_response_verified or not self.power_cut_response_verified:
                raise ValueError("PASS requires verified E-stop and power-cut response")
            kinds = {reference.kind for reference in self.evidence_refs}
            if EvidenceKind.MEASUREMENT not in kinds:
                raise ValueError("PASS requires a measurement artifact")
            if not ({EvidenceKind.VIDEO, EvidenceKind.TELEMETRY} & kinds):
                raise ValueError("PASS requires video or telemetry evidence")
        return self


def evidence_digest(evidence: SingleServoHilEvidence) -> str:
    """Return a deterministic content digest binding a permit to one evidence record."""
    payload = json.dumps(
        evidence.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
