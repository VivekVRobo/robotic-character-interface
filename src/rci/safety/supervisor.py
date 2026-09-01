"""Authoritative composition point for deterministic motion safety."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from uuid import UUID, uuid4

from rci.config.models import AppSettings
from rci.domain.enums import MotionDecision, SafetySeverity
from rci.safety.dynamics import assess_dynamic_motion_eligibility
from rci.safety.factory import build_safety_envelope, build_safety_lifecycle_policy
from rci.safety.lifecycle import (
    SafetyLifecycleController,
    SafetyLifecycleSnapshot,
    SafetyResetResult,
)
from rci.safety.models import (
    CartesianPoint,
    MotionCandidate,
    MotionDynamics,
    SafetyEnvelope,
    SafetyViolation,
    SafetyViolationCode,
)


@dataclass(frozen=True, slots=True)
class MotionAuthorization:
    """Immutable proof that one candidate passed the complete V1 safety stack.

    This is not a wire command and contains no PWM or actuator-driver values.
    RobotGateway will later translate this authorization into protocol data.
    """

    authorization_id: UUID
    lifecycle_sequence: int
    joint_targets_deg: Mapping[str, float]
    workspace_point_mm: CartesianPoint
    command_ttl_ms: float
    max_velocity_deg_s: float
    max_acceleration_deg_s2: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "joint_targets_deg",
            MappingProxyType(dict(self.joint_targets_deg)),
        )


@dataclass(frozen=True, slots=True)
class MotionSafetyResult:
    """Supervisor decision and optional authorization artifact."""

    decision: MotionDecision
    violations: tuple[SafetyViolation, ...]
    lifecycle: SafetyLifecycleSnapshot
    authorization: MotionAuthorization | None = None

    @property
    def approved(self) -> bool:
        return (
            self.decision is MotionDecision.APPROVE
            and not self.violations
            and self.authorization is not None
        )


class MotionSafetySupervisor:
    """Only application-layer authority allowed to mint MotionAuthorization."""

    def __init__(
        self,
        envelope: SafetyEnvelope,
        lifecycle: SafetyLifecycleController,
    ) -> None:
        policy = envelope.motion_policy
        if policy is not None and (
            policy.heartbeat_timeout_ms != lifecycle.policy.heartbeat_timeout_ms
        ):
            raise ValueError("dynamic and lifecycle heartbeat timeouts must match")
        self._envelope = envelope
        self._lifecycle = lifecycle

    @classmethod
    def from_settings(cls, settings: AppSettings) -> MotionSafetySupervisor:
        """Construct the complete supervisor from validated application settings."""
        return cls(
            build_safety_envelope(settings),
            SafetyLifecycleController(build_safety_lifecycle_policy(settings)),
        )

    @property
    def envelope(self) -> SafetyEnvelope:
        return self._envelope

    def lifecycle_snapshot(self) -> SafetyLifecycleSnapshot:
        return self._lifecycle.snapshot()

    def arm_watchdog(self) -> SafetyLifecycleSnapshot:
        return self._lifecycle.arm_watchdog()

    def disarm_watchdog(self) -> SafetyLifecycleSnapshot:
        return self._lifecycle.disarm_watchdog()

    def observe_heartbeat_age(self, heartbeat_age_ms: float) -> SafetyLifecycleSnapshot:
        return self._lifecycle.observe_heartbeat_age(heartbeat_age_ms)

    def trigger_software_estop(self, reason: str) -> SafetyLifecycleSnapshot:
        return self._lifecycle.trigger_software_estop(reason)

    def request_manual_reset(self) -> SafetyResetResult:
        return self._lifecycle.request_manual_reset()

    def evaluate(
        self,
        candidate: MotionCandidate,
        dynamics: MotionDynamics,
    ) -> MotionSafetyResult:
        """Compose lifecycle, static, and dynamic safety into one fail-closed decision."""
        self._lifecycle.set_physical_estop(candidate.estop_active)
        self._lifecycle.observe_heartbeat_age(dynamics.heartbeat_age_ms)
        lifecycle = self._lifecycle.snapshot()

        lifecycle_result = self._evaluate_lifecycle(lifecycle)
        if lifecycle_result is not None:
            return lifecycle_result

        eligibility = assess_dynamic_motion_eligibility(
            self._envelope,
            candidate,
            dynamics,
        )
        if not eligibility.approved:
            return MotionSafetyResult(
                decision=eligibility.decision,
                violations=eligibility.violations,
                lifecycle=lifecycle,
            )

        policy = self._envelope.motion_policy
        point = candidate.workspace_point_mm
        if policy is None or not policy.valid or point is None:
            return MotionSafetyResult(
                decision=MotionDecision.REJECT,
                violations=(
                    SafetyViolation(
                        SafetyViolationCode.MOTION_POLICY_UNAVAILABLE,
                        "approved safety result lacked a valid policy or workspace point",
                    ),
                ),
                lifecycle=lifecycle,
            )

        authorization = MotionAuthorization(
            authorization_id=uuid4(),
            lifecycle_sequence=lifecycle.sequence,
            joint_targets_deg=candidate.joint_targets_deg,
            workspace_point_mm=point,
            command_ttl_ms=policy.command_ttl_ms,
            max_velocity_deg_s=policy.max_velocity_deg_s,
            max_acceleration_deg_s2=policy.max_acceleration_deg_s2,
        )
        return MotionSafetyResult(
            decision=MotionDecision.APPROVE,
            violations=(),
            lifecycle=lifecycle,
            authorization=authorization,
        )

    @staticmethod
    def _evaluate_lifecycle(
        lifecycle: SafetyLifecycleSnapshot,
    ) -> MotionSafetyResult | None:
        if lifecycle.estop_latched or lifecycle.physical_estop_active:
            detail = lifecycle.latest_reason or "emergency-stop lifecycle is latched"
            return MotionSafetyResult(
                decision=MotionDecision.ESTOP,
                violations=(
                    SafetyViolation(
                        SafetyViolationCode.LIFECYCLE_ESTOP_LATCHED,
                        detail,
                        SafetySeverity.CRITICAL,
                    ),
                ),
                lifecycle=lifecycle,
            )

        if not lifecycle.watchdog_armed:
            return MotionSafetyResult(
                decision=MotionDecision.REJECT,
                violations=(
                    SafetyViolation(
                        SafetyViolationCode.WATCHDOG_NOT_ARMED,
                        "watchdog must be armed before motion can be authorized",
                    ),
                ),
                lifecycle=lifecycle,
            )

        if not lifecycle.watchdog_healthy:
            return MotionSafetyResult(
                decision=MotionDecision.REJECT,
                violations=(
                    SafetyViolation(
                        SafetyViolationCode.WATCHDOG_UNHEALTHY,
                        "watchdog must observe a fresh heartbeat before motion can be authorized",
                    ),
                ),
                lifecycle=lifecycle,
            )

        return None
