"""Single-servo hardware-in-the-loop readiness and activation gate."""

from rci.hil.gate import HilGateDecision, HilGateReason, SingleServoHilGate
from rci.hil.models import (
    HIL_EVIDENCE_SCHEMA_VERSION,
    HIL_PERMIT_SCHEMA_VERSION,
    HIL_RUN_RESULT_SCHEMA_VERSION,
    ElectricalEvidence,
    EvidenceKind,
    EvidenceReference,
    HilActivationPermit,
    HilRunOutcome,
    HilTargetObservation,
    MechanicalEvidence,
    ServoCalibrationEvidence,
    SingleServoHilEvidence,
    SingleServoHilRunResult,
    evidence_digest,
)

__all__ = [
    "HIL_EVIDENCE_SCHEMA_VERSION",
    "HIL_PERMIT_SCHEMA_VERSION",
    "HIL_RUN_RESULT_SCHEMA_VERSION",
    "ElectricalEvidence",
    "EvidenceKind",
    "EvidenceReference",
    "HilActivationPermit",
    "HilGateDecision",
    "HilGateReason",
    "HilRunOutcome",
    "HilTargetObservation",
    "MechanicalEvidence",
    "ServoCalibrationEvidence",
    "SingleServoHilEvidence",
    "SingleServoHilGate",
    "SingleServoHilRunResult",
    "evidence_digest",
]
