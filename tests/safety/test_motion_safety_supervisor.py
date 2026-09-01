from pathlib import Path

from rci.config.loader import ConfigLoader
from rci.domain.enums import MotionDecision, SystemState
from rci.safety.models import CartesianPoint, MotionCandidate, MotionDynamics
from rci.safety.supervisor import MotionSafetySupervisor


def test_canonical_configuration_cannot_authorize_physical_motion() -> None:
    settings = ConfigLoader(Path("configs")).load()
    supervisor = MotionSafetySupervisor.from_settings(settings)
    supervisor.arm_watchdog()
    supervisor.observe_heartbeat_age(0.0)

    result = supervisor.evaluate(
        MotionCandidate(
            system_state=SystemState.ARMED,
            estop_active=False,
            joint_targets_deg={"base": 0.0},
            workspace_point_mm=CartesianPoint(0.0, 0.0, 100.0),
        ),
        MotionDynamics(
            command_age_ms=0.0,
            heartbeat_age_ms=0.0,
            joint_velocities_deg_s={"base": 0.0},
            joint_accelerations_deg_s2={"base": 0.0},
        ),
    )

    assert result.decision is MotionDecision.REJECT
    assert result.authorization is None


def test_motion_authorization_can_only_be_minted_in_supervisor_module() -> None:
    source_root = Path("src/rci")
    violations: list[str] = []

    for path in source_root.rglob("*.py"):
        if path.as_posix() == "src/rci/safety/supervisor.py":
            continue
        if "MotionAuthorization(" in path.read_text(encoding="utf-8"):
            violations.append(path.as_posix())

    assert violations == []
