"""Dynamic velocity, acceleration, and freshness safety checks."""

from __future__ import annotations

from math import isfinite

from rci.domain.enums import MotionDecision
from rci.safety.eligibility import assess_motion_eligibility
from rci.safety.models import (
    MotionCandidate,
    MotionDynamics,
    MotionEligibility,
    SafetyEnvelope,
    SafetyViolation,
    SafetyViolationCode,
)


def _violation(code: SafetyViolationCode, detail: str) -> SafetyViolation:
    return SafetyViolation(code=code, detail=detail)


def assess_dynamic_motion_eligibility(
    envelope: SafetyEnvelope,
    candidate: MotionCandidate,
    dynamics: MotionDynamics,
) -> MotionEligibility:
    """Run static eligibility first, then dynamic and freshness checks."""
    static_result = assess_motion_eligibility(envelope, candidate)
    if not static_result.approved:
        return static_result

    policy = envelope.motion_policy
    if policy is None or not policy.valid:
        return MotionEligibility(
            decision=MotionDecision.REJECT,
            violations=(
                _violation(
                    SafetyViolationCode.MOTION_POLICY_UNAVAILABLE,
                    "dynamic motion policy is missing or invalid",
                ),
            ),
        )

    violations: list[SafetyViolation] = []

    if not isfinite(dynamics.command_age_ms) or dynamics.command_age_ms < 0:
        violations.append(
            _violation(
                SafetyViolationCode.COMMAND_AGE_INVALID,
                "command age must be a finite non-negative value",
            )
        )
    elif dynamics.command_age_ms > policy.command_ttl_ms:
        violations.append(
            _violation(
                SafetyViolationCode.COMMAND_STALE,
                f"command age {dynamics.command_age_ms} ms exceeds TTL {policy.command_ttl_ms} ms",
            )
        )

    if not isfinite(dynamics.heartbeat_age_ms) or dynamics.heartbeat_age_ms < 0:
        violations.append(
            _violation(
                SafetyViolationCode.HEARTBEAT_AGE_INVALID,
                "heartbeat age must be a finite non-negative value",
            )
        )
    elif dynamics.heartbeat_age_ms > policy.heartbeat_timeout_ms:
        violations.append(
            _violation(
                SafetyViolationCode.HEARTBEAT_STALE,
                (
                    f"heartbeat age {dynamics.heartbeat_age_ms} ms exceeds timeout "
                    f"{policy.heartbeat_timeout_ms} ms"
                ),
            )
        )

    target_names = set(candidate.joint_targets_deg)
    velocity_names = set(dynamics.joint_velocities_deg_s)
    acceleration_names = set(dynamics.joint_accelerations_deg_s2)

    for name in sorted(target_names - velocity_names):
        violations.append(
            _violation(
                SafetyViolationCode.VELOCITY_SAMPLE_MISSING,
                f"joint {name!r} is missing a velocity sample",
            )
        )
    for name in sorted(target_names - acceleration_names):
        violations.append(
            _violation(
                SafetyViolationCode.ACCELERATION_SAMPLE_MISSING,
                f"joint {name!r} is missing an acceleration sample",
            )
        )

    for name in sorted((velocity_names | acceleration_names) - set(envelope.joints)):
        violations.append(
            _violation(
                SafetyViolationCode.DYNAMIC_SAMPLE_UNKNOWN_JOINT,
                f"dynamic sample references unknown joint {name!r}",
            )
        )

    for name, velocity_deg_s in dynamics.joint_velocities_deg_s.items():
        if name not in target_names:
            continue
        if not isfinite(velocity_deg_s):
            violations.append(
                _violation(
                    SafetyViolationCode.INVALID_NUMERIC_TARGET,
                    f"joint {name!r} velocity is not finite",
                )
            )
        elif abs(velocity_deg_s) > policy.max_velocity_deg_s:
            violations.append(
                _violation(
                    SafetyViolationCode.VELOCITY_LIMIT_VIOLATION,
                    (
                        f"joint {name!r} velocity {velocity_deg_s} deg/s exceeds "
                        f"limit {policy.max_velocity_deg_s} deg/s"
                    ),
                )
            )

    for name, acceleration_deg_s2 in dynamics.joint_accelerations_deg_s2.items():
        if name not in target_names:
            continue
        if not isfinite(acceleration_deg_s2):
            violations.append(
                _violation(
                    SafetyViolationCode.INVALID_NUMERIC_TARGET,
                    f"joint {name!r} acceleration is not finite",
                )
            )
        elif abs(acceleration_deg_s2) > policy.max_acceleration_deg_s2:
            violations.append(
                _violation(
                    SafetyViolationCode.ACCELERATION_LIMIT_VIOLATION,
                    (
                        f"joint {name!r} acceleration {acceleration_deg_s2} deg/s^2 exceeds "
                        f"limit {policy.max_acceleration_deg_s2} deg/s^2"
                    ),
                )
            )

    if violations:
        return MotionEligibility(
            decision=MotionDecision.REJECT,
            violations=tuple(violations),
        )
    return MotionEligibility(decision=MotionDecision.APPROVE, violations=())
