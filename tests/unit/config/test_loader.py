from pathlib import Path
from shutil import copytree

import pytest
import yaml

from rci.config.loader import ConfigLoader
from rci.domain.enums import SystemState
from rci.domain.errors import ConfigurationError


def _config_copy(tmp_path: Path) -> Path:
    target = tmp_path / "configs"
    copytree("configs", target)
    return target


def _rewrite(path: Path, data: object) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_default_config_set_loads() -> None:
    settings = ConfigLoader(Path("configs")).load()
    assert settings.system.simulation is True
    assert settings.system.startup_state is SystemState.BOOT
    assert settings.safety.estop.require_manual_reset is True


def test_missing_config_file_fails_closed(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    (config_dir / "voice.yaml").unlink()

    with pytest.raises(ConfigurationError, match="unable to load"):
        ConfigLoader(config_dir).load()


def test_heartbeat_timeout_must_exceed_interval(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    path = config_dir / "safety.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["motion"]["heartbeat_timeout_ms"] = data["motion"]["heartbeat_interval_ms"]
    _rewrite(path, data)

    with pytest.raises(ConfigurationError, match="timeout must exceed"):
        ConfigLoader(config_dir).load()


def test_illegal_motion_state_fails_closed(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    path = config_dir / "safety.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["states"]["motion_allowed"].append("IDLE")
    _rewrite(path, data)

    with pytest.raises(ConfigurationError, match="motion cannot be enabled"):
        ConfigLoader(config_dir).load()


def test_verified_servos_require_measured_limits(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    path = config_dir / "servos.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["servos"]["hardware_verified"] = True
    _rewrite(path, data)

    with pytest.raises(ConfigurationError, match="requires min/neutral/max"):
        ConfigLoader(config_dir).load()


def test_non_simulation_mode_requires_verified_hardware(tmp_path: Path) -> None:
    config_dir = _config_copy(tmp_path)
    path = config_dir / "system.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["system"]["simulation"] = False
    _rewrite(path, data)

    with pytest.raises(ConfigurationError, match="requires verified robot and servo"):
        ConfigLoader(config_dir).load()
