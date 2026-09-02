from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_api_cannot_construct_actuator_level_commands() -> None:
    api_root = ROOT / "src" / "rci" / "api"
    source = "\n".join(path.read_text(encoding="utf-8") for path in api_root.glob("*.py"))
    for forbidden in (
        "ValidatedMotionCommand(",
        "MotionAuthorization(",
        "JointTarget(",
        "setPWM(",
        "analogWrite(",
        "Servo.write(",
    ):
        assert forbidden not in source
