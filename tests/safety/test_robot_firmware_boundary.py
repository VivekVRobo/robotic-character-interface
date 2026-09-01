from pathlib import Path

ROBOT_FIRMWARE_FILES = (
    Path("firmware/robot/robot.ino"),
    Path("firmware/robot/runtime.h"),
)

FORBIDDEN_ACTUATOR_TOKENS = (
    "PCA9685",
    "Adafruit_PWMServoDriver",
    "Servo.h",
    "setPWM(",
    "set_pwm(",
    "servo.write(",
    "analogWrite(",
)


def test_pr012_robot_firmware_has_no_actuator_api() -> None:
    for path in ROBOT_FIRMWARE_FILES:
        source = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_ACTUATOR_TOKENS:
            assert token not in source, f"{path} must not contain actuator token {token!r}"


def test_validated_motion_is_explicitly_deferred() -> None:
    runtime_source = Path("firmware/robot/runtime.h").read_text(encoding="utf-8")

    assert "kMotionDeferred" in runtime_source
    assert "no actuator layer" in runtime_source
