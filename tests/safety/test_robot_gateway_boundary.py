from pathlib import Path


ALLOWED_VALIDATED_MOTION_CONSTRUCTORS = {
    Path("src/rci/hardware/robot_gateway.py"),
    Path("src/rci/protocols/messages.py"),
}


def test_only_robot_gateway_constructs_validated_motion_in_application_code() -> None:
    offenders: list[str] = []
    for path in Path("src/rci").rglob("*.py"):
        if path in ALLOWED_VALIDATED_MOTION_CONSTRUCTORS:
            continue
        source = path.read_text(encoding="utf-8")
        if "ValidatedMotionCommand(" in source:
            offenders.append(str(path))

    assert offenders == [], (
        "ValidatedMotionCommand construction bypasses RobotGateway: " + ", ".join(offenders)
    )


def test_gateway_is_only_application_module_emitting_validated_motion_type() -> None:
    offenders: list[str] = []
    for path in Path("src/rci").rglob("*.py"):
        if path == Path("src/rci/hardware/robot_gateway.py"):
            continue
        if path.parts[-2] == "protocols":
            continue
        source = path.read_text(encoding="utf-8")
        if "MessageType.VALIDATED_MOTION_COMMAND" in source:
            offenders.append(str(path))

    assert offenders == [], (
        "validated motion wire type emitted outside RobotGateway: " + ", ".join(offenders)
    )
