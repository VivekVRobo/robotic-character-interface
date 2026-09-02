import ast
from pathlib import Path

ALLOWED_VALIDATED_MOTION_CONSTRUCTORS = {
    Path("src/rci/hardware/robot_gateway.py"),
    Path("src/rci/protocols/messages.py"),
}


def _is_validated_motion_type(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "VALIDATED_MOTION_COMMAND"
        and isinstance(node.value, ast.Name)
        and node.value.id == "MessageType"
    )


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


def test_gateway_is_only_application_module_passing_validated_motion_type_to_calls() -> None:
    """Receiving/comparing the wire type is allowed; emitting/passing it is gateway-only."""
    offenders: list[str] = []
    for path in Path("src/rci").rglob("*.py"):
        if path == Path("src/rci/hardware/robot_gateway.py"):
            continue
        if path.parts[-2] == "protocols":
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            if any(_is_validated_motion_type(node) for node in ast.walk(call)):
                offenders.append(str(path))
                break

    assert offenders == [], (
        "validated motion wire type passed to a call outside RobotGateway: " + ", ".join(offenders)
    )
