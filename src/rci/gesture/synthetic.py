"""Synthetic glove traces for software-only gesture testing and demos."""

from __future__ import annotations

from rci.protocols.messages import GloveTelemetry


def synthetic_tilt(
    *,
    roll_deg: float = 0.0,
    pitch_deg: float = 0.0,
    time_ms: int = 0,
) -> GloveTelemetry:
    return GloveTelemetry(
        device_time_ms_mod=time_ms & 0xFFFF,
        accel_x_mg=0,
        accel_y_mg=0,
        accel_z_mg=1000,
        gyro_x_cdeg_s=0,
        gyro_y_cdeg_s=0,
        gyro_z_cdeg_s=0,
        pitch_cdeg=round(pitch_deg * 100),
        roll_cdeg=round(roll_deg * 100),
        battery_mv=4000,
        flags=0,
    )


def synthetic_wave(*, start_ms: int = 0) -> tuple[GloveTelemetry, ...]:
    rolls = (-14.0, 14.0, -15.0, 15.0, -16.0, 16.0, -14.0, 14.0)
    return tuple(
        synthetic_tilt(roll_deg=roll, time_ms=start_ms + index * 20)
        for index, roll in enumerate(rolls)
    )
