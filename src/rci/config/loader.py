"""YAML configuration loader with strict model and cross-file validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from rci.config.models import (
    AppSettings,
    CognitionSettings,
    IMUSettings,
    RadioSettings,
    RobotSettings,
    SafetySettings,
    ServosSettings,
    SystemSettings,
    VoiceSettings,
)
from rci.config.paths import default_config_dir
from rci.config.validator import validate_app_settings
from rci.domain.errors import ConfigurationError


class ConfigLoader:
    """Load the canonical config set from a directory."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = default_config_dir() if config_dir is None else config_dir

    def _read_yaml(self, filename: str) -> dict[str, Any]:
        path = self.config_dir / filename
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"unable to load {path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise ConfigurationError(f"configuration file {path} must contain a mapping")
        return raw

    @staticmethod
    def _section(raw: dict[str, Any], key: str, filename: str) -> dict[str, Any]:
        section = raw.get(key)
        if not isinstance(section, dict):
            raise ConfigurationError(f"{filename} must contain a {key!r} mapping")
        return section

    def load(self) -> AppSettings:
        """Load and validate all configuration files or fail before runtime starts."""
        try:
            system_raw = self._read_yaml("system.yaml")
            safety_raw = self._read_yaml("safety.yaml")
            robot_raw = self._read_yaml("robot.yaml")
            servos_raw = self._read_yaml("servos.yaml")
            imu_raw = self._read_yaml("imu.yaml")
            radio_raw = self._read_yaml("radio.yaml")
            voice_raw = self._read_yaml("voice.yaml")
            cognition_raw = self._read_yaml("cognition.yaml")

            settings = AppSettings(
                system=SystemSettings.model_validate(
                    self._section(system_raw, "system", "system.yaml")
                ),
                safety=SafetySettings.model_validate(safety_raw),
                robot=RobotSettings.model_validate(self._section(robot_raw, "robot", "robot.yaml")),
                servos=ServosSettings.model_validate(
                    self._section(servos_raw, "servos", "servos.yaml")
                ),
                imu=IMUSettings.model_validate(imu_raw),
                radio=RadioSettings.model_validate(self._section(radio_raw, "radio", "radio.yaml")),
                voice=VoiceSettings.model_validate(self._section(voice_raw, "voice", "voice.yaml")),
                cognition=CognitionSettings.model_validate(
                    self._section(cognition_raw, "cognition", "cognition.yaml")
                ),
            )
        except ValidationError as exc:
            raise ConfigurationError(f"configuration validation failed: {exc}") from exc

        validate_app_settings(settings)
        return settings
