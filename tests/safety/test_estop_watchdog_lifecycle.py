from pathlib import Path

from rci.config.loader import ConfigLoader
from rci.safety.factory import build_safety_lifecycle_policy
from rci.safety.lifecycle import SafetyLifecycleController, SafetyStopCause


def test_canonical_watchdog_timeout_requires_manual_reset_before_motion_can_resume() -> None:
    settings = ConfigLoader(Path("configs")).load()
    controller = SafetyLifecycleController(build_safety_lifecycle_policy(settings))

    assert controller.snapshot().motion_blocked

    controller.arm_watchdog()
    controller.observe_heartbeat_age(0.0)
    assert not controller.snapshot().motion_blocked

    timed_out = controller.observe_heartbeat_age(
        float(settings.safety.motion.heartbeat_timeout_ms) + 0.1
    )
    assert timed_out.estop_latched
    assert timed_out.motion_blocked
    assert SafetyStopCause.WATCHDOG_TIMEOUT in timed_out.causes

    controller.observe_heartbeat_age(0.0)
    assert controller.snapshot().watchdog_healthy
    assert controller.snapshot().estop_latched
    assert controller.snapshot().motion_blocked

    reset = controller.request_manual_reset()
    assert reset.cleared
    assert not reset.snapshot.motion_blocked
