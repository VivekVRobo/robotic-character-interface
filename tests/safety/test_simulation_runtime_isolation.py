from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_production_servo_config_remains_hardware_unverified() -> None:
    servos = yaml.safe_load((ROOT / "configs" / "servos.yaml").read_text(encoding="utf-8"))
    assert servos["servos"]["hardware_verified"] is False


def test_physical_firmware_has_no_simulation_runtime_dependency() -> None:
    firmware = (ROOT / "firmware" / "robot" / "robot.ino").read_text(encoding="utf-8")
    lowered = firmware.lower()
    assert "digitaltwin" not in lowered
    assert "digital_twin" not in lowered
    assert "build_simulation_supervisor" not in lowered
    assert "simulationruntime" not in lowered


def test_synthetic_verified_envelope_is_confined_to_simulation_namespace() -> None:
    forbidden_roots = [ROOT / "src" / "rci" / "hardware", ROOT / "src" / "rci" / "safety"]
    for root in forbidden_roots:
        source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
        assert "build_simulation_supervisor" not in source
