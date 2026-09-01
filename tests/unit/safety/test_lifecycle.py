from math import nan
from pathlib import Path

import pytest

from rci.config.loader import ConfigLoader
from rci.config.models import EStopSettings
from rci.config.validator import validate_app_settings
from rci.domain.errors import ConfigurationError
from rci.safety.factory import build_safety_lifecycle_policy
from rci.safety.lifecycle import (
    SafetyLifecycleController,
    SafetyLifecyclePolicy,
    SafetyResetDenial,
    SafetyStopCause,
)


def _controller(timeout_ms: float = 500.0) -> SafetyLifecycleController:
    return SafetyLifecycleController(
        SafetyLifecyclePolicy(
            heartbeat_timeout_ms=timeout_ms,
            require_manual_reset=True,
        )
    )


def _healthy_controller() -> SafetyLifecycleController:
    controller = _controller()
    controller.arm_watchdog()
    controller.observe_heartbeat_age(0.0)
    return controller


def test_watchdog_starts_fail_closed_until_fresh_heartbeat() -> None:
    controller = _controller()

    assert controller.snapshot().motion_blocked
    armed = controller.arm_watchdog()
    assert armed.watchdog_armed
    assert not armed.watchdog_healthy
    assert armed.motion_blocked

    healthy = controller.observe_heartbeat_age(500.0)
    assert healthy.watchdog_healthy
    assert not healthy.motion_blocked


def test_watchdog_timeout_latches_estop_and_recovery_does_not_auto_clear() -> None:
    controller = _healthy_controller()

    expired = controller.observe_heartbeat_age(500.01)
    assert expired.estop_latched
    assert expired.motion_blocked
    assert SafetyStopCause.WATCHDOG_TIMEOUT in expired.causes

    recovered = controller.observe_heartbeat_age(0.0)
    assert recovered.watchdog_healthy
    assert recovered.estop_latched
    assert recovered.motion_blocked

    reset = controller.request_manual_reset()
    assert reset.cleared
    assert not reset.snapshot.estop_latched
    assert not reset.snapshot.motion_blocked


def test_invalid_watchdog_age_latches_fail_closed() -> None:
    controller = _healthy_controller()

    snapshot = controller.observe_heartbeat_age(nan)

    assert snapshot.estop_latched
    assert not snapshot.watchdog_healthy
    assert SafetyStopCause.WATCHDOG_INVALID in snapshot.causes


def test_physical_estop_release_does_not_clear_latch() -> None:
    controller = _healthy_controller()

    pressed = controller.set_physical_estop(True)
    assert pressed.physical_estop_active
    assert pressed.estop_latched
    assert SafetyStopCause.HARDWARE_ESTOP in pressed.causes

    released = controller.set_physical_estop(False)
    assert not released.physical_estop_active
    assert released.estop_latched
    assert released.motion_blocked

    reset = controller.request_manual_reset()
    assert reset.cleared
    assert not reset.snapshot.motion_blocked


def test_manual_reset_is_denied_while_physical_estop_is_active() -> None:
    controller = _healthy_controller()
    controller.set_physical_estop(True)

    result = controller.request_manual_reset()

    assert not result.cleared
    assert result.denials == (SafetyResetDenial.PHYSICAL_ESTOP_ACTIVE,)
    assert result.snapshot.estop_latched


def test_manual_reset_is_denied_until_watchdog_is_armed_and_healthy() -> None:
    controller = _controller()
    controller.trigger_software_estop("operator stop")

    disarmed = controller.request_manual_reset()
    assert not disarmed.cleared
    assert disarmed.denials == (SafetyResetDenial.WATCHDOG_NOT_ARMED,)

    controller.arm_watchdog()
    unhealthy = controller.request_manual_reset()
    assert not unhealthy.cleared
    assert unhealthy.denials == (SafetyResetDenial.WATCHDOG_UNHEALTHY,)

    controller.observe_heartbeat_age(0.0)
    cleared = controller.request_manual_reset()
    assert cleared.cleared


def test_software_estop_is_sticky_and_reason_is_preserved() -> None:
    controller = _healthy_controller()

    snapshot = controller.trigger_software_estop("operator requested stop")

    assert snapshot.estop_latched
    assert snapshot.latest_reason == "operator requested stop"
    assert SafetyStopCause.SOFTWARE_ESTOP in snapshot.causes


def test_multiple_stop_causes_accumulate_until_manual_reset() -> None:
    controller = _healthy_controller()
    controller.trigger_software_estop("software stop")
    controller.set_physical_estop(True)
    controller.observe_heartbeat_age(501.0)

    snapshot = controller.snapshot()
    assert snapshot.causes == frozenset(
        {
            SafetyStopCause.SOFTWARE_ESTOP,
            SafetyStopCause.HARDWARE_ESTOP,
            SafetyStopCause.WATCHDOG_TIMEOUT,
        }
    )

    controller.set_physical_estop(False)
    controller.observe_heartbeat_age(0.0)
    reset = controller.request_manual_reset()
    assert reset.cleared
    assert reset.snapshot.causes == frozenset()


def test_watchdog_disarm_blocks_motion_without_erasing_existing_latch() -> None:
    controller = _healthy_controller()
    controller.trigger_software_estop("stop")

    snapshot = controller.disarm_watchdog()

    assert snapshot.estop_latched
    assert not snapshot.watchdog_armed
    assert snapshot.motion_blocked


def test_reset_without_latch_is_explicit_noop() -> None:
    controller = _healthy_controller()

    result = controller.request_manual_reset()

    assert not result.cleared
    assert result.denials == (SafetyResetDenial.NO_LATCH,)


def test_invalid_lifecycle_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        SafetyLifecycleController(
            SafetyLifecyclePolicy(
                heartbeat_timeout_ms=500.0,
                require_manual_reset=False,
            )
        )


def test_policy_is_derived_from_canonical_safety_config() -> None:
    settings = ConfigLoader(Path("configs")).load()

    policy = build_safety_lifecycle_policy(settings)

    assert policy.heartbeat_timeout_ms == 500.0
    assert policy.require_manual_reset
    assert policy.valid


def test_v1_configuration_rejects_auto_reset_policy() -> None:
    settings = ConfigLoader(Path("configs")).load()
    unsafe_safety = settings.safety.model_copy(
        update={"estop": EStopSettings(require_manual_reset=False)}
    )
    unsafe_settings = settings.model_copy(update={"safety": unsafe_safety})

    with pytest.raises(ConfigurationError, match="manual emergency-stop reset"):
        validate_app_settings(unsafe_settings)
