"""Deterministic fail-closed motion eligibility checks."""

from __future__ import annotations

from math import isfinite

from rci.domain.enums import MotionDecision, SafetySeverity
from rci.safety.models import (
    MotionCandidate,
    MotionEligibility,
    SafetyEnvelope,
    SafetyViolation,
    SafetyViolationCode,
)


def _violation(
    code: SafetyViolationCode,
    detail: str,
    severity: SafetySeverity = SafetySeverity.CRITICAL,
) -> SafetyViolation:
    return SafetyViolation(code=code, detail=detail, severity=severity)


def assess_motion_eligibility(
    envelope: SafetyEnvelope,
    candidate: MotionCandidate,
) -> MotionEligibility:
    """Decide whether a candidate may advance to later dynamic safety checks."""
    if candidate.estop_active:
        return MotionEligibility(
            decision=MotionDecision.ESTOP,
            violations=(
                _violation(
                    SafetyViolationCode.ESTOP_ACTIVE,
                    "emergency stop is active",
                ),
            ),
        )

    violations: list[SafetyViolation] = []

    if candidate.system_state not in envelope.allowed_states:
        violations.append(
            _violation(
                SafetyViolationCode.STATE_NOT_ALLOWED,
                f"motion is not allowed in state {candidate.system_state.value}",
            )
        )

    if not candidate.joint_targets_deg:
        violations.append(
            _violation(
                SafetyViolationCode.EMPTY_JOINT_TARGETS,
                "candidate contains no joint targets",
            )
        )

    if not envelope.servos_verified:
        violations.append(
            _violation(
                SafetyViolationCode.JOINT_MODEL_UNVERIFIED,
                "servo hardware and measured joint limits are not verified",
            )
        )
    else:
        for name, target_deg in candidate.joint_targets_deg.items():
            if not isfinite(target_deg):
                violations.append(
                    _violation(
                        SafetyViolationCode.INVALID_NUMERIC_TARGET,
                        f"joint {name!r} target is not finite",
                    )
                )
                continue

            constraint = envelope.joints.get(name)
            if constraint is None:
                violations.append(
                    _violation(
                        SafetyViolationCode.UNKNOWN_JOINT,
                        f"joint {name!r} is not present in the verified model",
                    )
                )
                continue
            if not constraint.verified_complete:
                violations.append(
                    _violation(
                        SafetyViolationCode.JOINT_MODEL_UNVERIFIED,
                        f"joint {name!r} does not have verified min/neutral/max limits",
                    )
                )
                continue
            if not constraint.contains(target_deg):
                violations.append(
                    _violation(
                        SafetyViolationCode.JOINT_LIMIT_VIOLATION,
                        f"joint {name!r} target {target_deg} deg is outside verified limits",
                    )
                )

    if not envelope.robot_verified:
        violations.append(
            _violation(
                SafetyViolationCode.WORKSPACE_MODEL_UNVERIFIED,
                "robot geometry and workspace are not verified",
            )
        )
    elif not envelope.workspace.verified_complete:
        violations.append(
            _violation(
                SafetyViolationCode.WORKSPACE_MODEL_UNVERIFIED,
                "workspace does not contain a complete verified axis envelope",
            )
        )
    elif candidate.workspace_point_mm is None:
        violations.append(
            _violation(
                SafetyViolationCode.WORKSPACE_TARGET_REQUIRED,
                "candidate must include a workspace point for physical eligibility",
            )
        )
    elif not candidate.workspace_point_mm.finite:
        violations.append(
            _violation(
                SafetyViolationCode.INVALID_NUMERIC_TARGET,
                "workspace target contains a non-finite coordinate",
            )
        )
    elif not envelope.workspace.contains(candidate.workspace_point_mm):
        violations.append(
            _violation(
                SafetyViolationCode.WORKSPACE_LIMIT_VIOLATION,
                "workspace target lies outside the verified physical envelope",
            )
        )

    if violations:
        return MotionEligibility(
            decision=MotionDecision.REJECT,
            violations=tuple(violations),
        )
    return MotionEligibility(decision=MotionDecision.APPROVE, violations=())
