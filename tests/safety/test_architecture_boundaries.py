from pathlib import Path

FORBIDDEN_ACTUATOR_TOKENS = (
    "PCA9685",
    "ServoKit",
    "setPWM(",
    "set_pwm(",
)


def test_non_hardware_python_modules_do_not_reference_actuator_libraries() -> None:
    root = Path("src/rci")
    violations: list[str] = []

    for path in root.rglob("*.py"):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] == "hardware":
            continue

        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_ACTUATOR_TOKENS:
            if token in text:
                violations.append(f"{relative}: {token}")

    message = "Direct actuator references outside hardware boundary: " + ", ".join(violations)
    assert not violations, message


def test_glove_firmware_does_not_define_servo_angle_control_packet() -> None:
    glove = Path("firmware/glove/glove.ino").read_text(encoding="utf-8")
    forbidden = ("baseAngle", "shoulderAngle", "elbowAngle", "gripperAngle")
    assert not any(token in glove for token in forbidden)
