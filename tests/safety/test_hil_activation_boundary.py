from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_production_servo_config_remains_globally_unverified() -> None:
    raw = yaml.safe_load((ROOT / "configs" / "servos.yaml").read_text(encoding="utf-8"))
    servos = raw["servos"]

    assert servos["hardware_verified"] is False
    for joint in servos["joints"].values():
        assert joint["min_deg"] is None
        assert joint["max_deg"] is None
        assert joint["neutral_deg"] is None


def test_normal_robot_firmware_does_not_include_or_call_hil_driver_layer() -> None:
    source = (ROOT / "firmware" / "robot" / "robot.ino").read_text(encoding="utf-8")
    assert "hil_single_servo.h" not in source
    assert "setPWM(" not in source
    assert "analogWrite(" not in source
    assert "Servo.write(" not in source


def test_hil_permit_is_not_consumed_by_normal_application_modules() -> None:
    forbidden = "HilActivationPermit"
    offenders: list[str] = []
    for path in (ROOT / "src" / "rci").rglob("*.py"):
        relative = path.relative_to(ROOT / "src" / "rci")
        if relative.parts and relative.parts[0] == "hil":
            continue
        if forbidden in path.read_text(encoding="utf-8"):
            offenders.append(str(relative))
    assert offenders == []


def test_hil_firmware_guard_contains_no_actuator_write_api() -> None:
    source = (ROOT / "firmware" / "robot" / "hil_single_servo.h").read_text(encoding="utf-8")
    assert "kEligibleForDriverLayer" in source
    assert "setPWM(" not in source
    assert "analogWrite(" not in source
    assert "Servo.write(" not in source
