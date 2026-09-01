"""Latched E-stop and watchdog lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import isfinite


class SafetyStopCause(StrEnum):
    """Reasons that can latch the safety lifecycle into a stopped state."""

    HARDWARE_ESTOP = "HARDWARE_ESTOP"
    SOFTWARE_ESTOP = "SOFTWARE_ESTOP"
    WATCHDOG_TIMEOUT = "WATCHDOG_TIMEOUT"
    WATCHDOG_INVALID = "WATCHDOG_INVALID"


class SafetyResetDenial(StrEnum):
    """Machine-readable reasons a manual reset request was refused."""

    NO_LATCH = "NO_LATCH"
    PHYSICAL_ESTOP_ACTIVE = "PHYSICAL_ESTOP_ACTIVE"
    WATCHDOG_NOT_ARMED = "WATCHDOG_NOT_ARMED"
    WATCHDOG_UNHEALTHY = "WATCHDOG_UNHEALTHY"


@dataclass(frozen=True, slots=True)
class SafetyLifecyclePolicy:
    """Watchdog and reset policy derived from validated safety configuration."""

    heartbeat_timeout_ms: float
    require_manual_reset: bool = True

    @property
    def valid(self) -> bool:
        return (
            isfinite(self.heartbeat_timeout_ms)
            and self.heartbeat_timeout_ms > 0
            and self.require_manual_reset
        )


@dataclass(frozen=True, slots=True)
class SafetyLifecycleSnapshot:
    """Immutable safety-lifecycle state consumed by the motion supervisor."""

    sequence: int = 0
    watchdog_armed: bool = False
    watchdog_healthy: bool = False
    physical_estop_active: bool = False
    estop_latched: bool = False
    causes: frozenset[SafetyStopCause] = frozenset()
    latest_reason: str | None = None

    @property
    def motion_blocked(self) -> bool:
        return (
            self.estop_latched
            or self.physical_estop_active
            or not self.watchdog_armed
            or not self.watchdog_healthy
        )


@dataclass(frozen=True, slots=True)
class SafetyResetResult:
    """Outcome of an explicit manual reset request."""

    cleared: bool
    snapshot: SafetyLifecycleSnapshot
    denials: tuple[SafetyResetDenial, ...] = ()


class SafetyLifecycleController:
    """Deterministic sticky E-stop/watchdog lifecycle controller.

    The controller intentionally has no timers or background tasks. Callers provide
    observed heartbeat age, which keeps unit tests and the future supervisor fully
    deterministic and monotonic-clock friendly.
    """

    def __init__(self, policy: SafetyLifecyclePolicy) -> None:
        if not policy.valid:
            raise ValueError(
                "safety lifecycle policy must require manual reset and a positive timeout"
            )
        self._policy = policy
        self._snapshot = SafetyLifecycleSnapshot()

    @property
    def policy(self) -> SafetyLifecyclePolicy:
        return self._policy

    def snapshot(self) -> SafetyLifecycleSnapshot:
        return self._snapshot

    def _commit(self, **changes: object) -> SafetyLifecycleSnapshot:
        updated = replace(
            self._snapshot,
            sequence=self._snapshot.sequence + 1,
            **changes,
        )
        self._snapshot = updated
        return updated

    def _latch(
        self,
        cause: SafetyStopCause,
        reason: str,
        **changes: object,
    ) -> SafetyLifecycleSnapshot:
        causes = frozenset((*self._snapshot.causes, cause))
        return self._commit(
            estop_latched=True,
            causes=causes,
            latest_reason=reason,
            **changes,
        )

    def arm_watchdog(self) -> SafetyLifecycleSnapshot:
        """Arm the watchdog in unhealthy state until a fresh heartbeat is observed."""
        if self._snapshot.watchdog_armed:
            return self._snapshot
        return self._commit(watchdog_armed=True, watchdog_healthy=False)

    def disarm_watchdog(self) -> SafetyLifecycleSnapshot:
        """Disarm watchdog monitoring; motion remains blocked while disarmed."""
        if not self._snapshot.watchdog_armed and not self._snapshot.watchdog_healthy:
            return self._snapshot
        return self._commit(watchdog_armed=False, watchdog_healthy=False)

    def observe_heartbeat_age(self, heartbeat_age_ms: float) -> SafetyLifecycleSnapshot:
        """Update watchdog health and latch on invalid/stale heartbeat age."""
        if not self._snapshot.watchdog_armed:
            return self._snapshot

        if not isfinite(heartbeat_age_ms) or heartbeat_age_ms < 0:
            return self._latch(
                SafetyStopCause.WATCHDOG_INVALID,
                "watchdog heartbeat age must be finite and non-negative",
                watchdog_healthy=False,
            )

        if heartbeat_age_ms > self._policy.heartbeat_timeout_ms:
            return self._latch(
                SafetyStopCause.WATCHDOG_TIMEOUT,
                (
                    f"watchdog heartbeat age {heartbeat_age_ms} ms exceeds timeout "
                    f"{self._policy.heartbeat_timeout_ms} ms"
                ),
                watchdog_healthy=False,
            )

        if self._snapshot.watchdog_healthy:
            return self._snapshot
        return self._commit(watchdog_healthy=True)

    def set_physical_estop(self, active: bool) -> SafetyLifecycleSnapshot:
        """Latch immediately when the independent physical E-stop is asserted."""
        if active:
            return self._latch(
                SafetyStopCause.HARDWARE_ESTOP,
                "physical emergency stop asserted",
                physical_estop_active=True,
            )

        if not self._snapshot.physical_estop_active:
            return self._snapshot
        return self._commit(physical_estop_active=False)

    def trigger_software_estop(self, reason: str) -> SafetyLifecycleSnapshot:
        """Latch an explicit software emergency-stop request."""
        normalized = reason.strip() or "software emergency stop requested"
        return self._latch(SafetyStopCause.SOFTWARE_ESTOP, normalized)

    def request_manual_reset(self) -> SafetyResetResult:
        """Clear the sticky E-stop only after every reset precondition is healthy."""
        snapshot = self._snapshot
        if not snapshot.estop_latched:
            return SafetyResetResult(
                cleared=False,
                snapshot=snapshot,
                denials=(SafetyResetDenial.NO_LATCH,),
            )

        denials: list[SafetyResetDenial] = []
        if snapshot.physical_estop_active:
            denials.append(SafetyResetDenial.PHYSICAL_ESTOP_ACTIVE)
        if not snapshot.watchdog_armed:
            denials.append(SafetyResetDenial.WATCHDOG_NOT_ARMED)
        elif not snapshot.watchdog_healthy:
            denials.append(SafetyResetDenial.WATCHDOG_UNHEALTHY)

        if denials:
            return SafetyResetResult(
                cleared=False,
                snapshot=snapshot,
                denials=tuple(denials),
            )

        cleared = self._commit(
            estop_latched=False,
            causes=frozenset(),
            latest_reason="manual emergency-stop reset completed",
        )
        return SafetyResetResult(cleared=True, snapshot=cleared)
