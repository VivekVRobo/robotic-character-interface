import pytest
from pydantic import ValidationError

from rci.config.models import RadioSettings, SafetyMotionSettings


def test_radio_channel_is_bounded() -> None:
    with pytest.raises(ValidationError):
        RadioSettings(
            module="nRF24L01+",
            channel=126,
            data_rate="250KBPS",
            glove_to_gateway_pipe="a",
            gateway_to_glove_pipe="b",
        )


def test_safety_motion_limits_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        SafetyMotionSettings(
            command_ttl_ms=250,
            heartbeat_interval_ms=100,
            heartbeat_timeout_ms=500,
            max_velocity_deg_s=0,
            max_acceleration_deg_s2=180,
        )
