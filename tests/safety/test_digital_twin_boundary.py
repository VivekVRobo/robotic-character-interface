from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_physical_robot_firmware_does_not_include_digital_twin() -> None:
    source = (ROOT / "firmware" / "robot" / "robot.ino").read_text(encoding="utf-8")
    assert "digital_twin" not in source.lower()
    assert "simulated_driver" not in source.lower()


def test_digital_twin_only_consumes_semantic_validated_motion_commands() -> None:
    source = (ROOT / "src" / "rci" / "simulation" / "digital_twin.py").read_text(encoding="utf-8")
    assert "ValidatedMotionCommand" in source
    assert "setPWM(" not in source
    assert "analogWrite(" not in source
    assert "Servo.write(" not in source
