from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_reference_profile_is_not_loaded_by_production_config_set() -> None:
    production_robot = yaml.safe_load((ROOT / "configs" / "robot.yaml").read_text(encoding="utf-8"))
    production_servos = yaml.safe_load(
        (ROOT / "configs" / "servos.yaml").read_text(encoding="utf-8")
    )
    reference = yaml.safe_load(
        (ROOT / "configs" / "simulation" / "reference_arm.yaml").read_text(encoding="utf-8")
    )["reference_robot"]

    assert reference["simulation_only"] is True
    assert reference["hardware_verified"] is False
    assert production_robot["robot"]["hardware_verified"] is False
    assert production_servos["servos"]["hardware_verified"] is False
    assert production_robot["robot"]["links"]["shoulder_mm"] is None
    assert production_robot["robot"]["links"]["forearm_mm"] is None
    for joint in production_servos["servos"]["joints"].values():
        assert joint["min_deg"] is None
        assert joint["max_deg"] is None
        assert joint["neutral_deg"] is None


def test_reference_profile_is_only_consumed_by_robotics_or_tests() -> None:
    token = "reference_arm.yaml"
    offenders: list[str] = []
    for path in (ROOT / "src" / "rci").rglob("*.py"):
        relative = path.relative_to(ROOT / "src" / "rci")
        if relative.parts and relative.parts[0] == "robotics":
            continue
        if token in path.read_text(encoding="utf-8"):
            offenders.append(str(relative))
    assert offenders == []
