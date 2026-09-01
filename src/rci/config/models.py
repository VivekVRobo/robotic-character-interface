"""Pydantic models for all V1 runtime configuration files."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rci.domain.enums import SystemState


class SystemSettings(BaseModel):
    environment: str = "development"
    name: str = "robotic-character-interface"
    simulation: bool = True
    startup_state: SystemState = SystemState.BOOT


class SafetyMotionSettings(BaseModel):
    command_ttl_ms: int = Field(gt=0)
    heartbeat_interval_ms: int = Field(gt=0)
    heartbeat_timeout_ms: int = Field(gt=0)
    max_velocity_deg_s: float = Field(gt=0)
    max_acceleration_deg_s2: float = Field(gt=0)


class SafetyStateSettings(BaseModel):
    motion_allowed: list[SystemState]


class EStopSettings(BaseModel):
    require_manual_reset: bool = True


class SafetySettings(BaseModel):
    motion: SafetyMotionSettings
    states: SafetyStateSettings
    estop: EStopSettings


class RobotLinksSettings(BaseModel):
    shoulder_mm: float | None = Field(default=None, gt=0)
    forearm_mm: float | None = Field(default=None, gt=0)


class RobotPoseSettings(BaseModel):
    home: dict[str, float] = Field(default_factory=dict)
    safe: dict[str, float] = Field(default_factory=dict)


class RobotWorkspaceSettings(BaseModel):
    min_x_mm: float | None = None
    max_x_mm: float | None = None
    min_y_mm: float | None = None
    max_y_mm: float | None = None
    min_z_mm: float | None = None
    max_z_mm: float | None = None


class RobotSettings(BaseModel):
    hardware_verified: bool = False
    links: RobotLinksSettings
    poses: RobotPoseSettings
    workspace: RobotWorkspaceSettings


class ServoJointSettings(BaseModel):
    channel: int = Field(ge=0, le=15)
    protocol_id: int | None = Field(default=None, ge=1, le=255)
    min_deg: float | None = None
    max_deg: float | None = None
    neutral_deg: float | None = None


class ServosSettings(BaseModel):
    hardware_verified: bool = False
    driver: str
    pwm_frequency_hz: float = Field(gt=0)
    joints: dict[str, ServoJointSettings]


class IMUDeviceSettings(BaseModel):
    sensor: str
    sample_rate_hz: int = Field(gt=0)
    accel_range_g: float = Field(gt=0)
    gyro_range_dps: float = Field(gt=0)


class IMUFilterSettings(BaseModel):
    type: str
    alpha: float = Field(gt=0, lt=1)
    dead_zone_pitch_deg: float = Field(ge=0)
    dead_zone_roll_deg: float = Field(ge=0)


class IMUCalibrationSettings(BaseModel):
    hardware_verified: bool = False


class IMUSettings(BaseModel):
    imu: IMUDeviceSettings
    filter: IMUFilterSettings
    calibration: IMUCalibrationSettings


class RadioSettings(BaseModel):
    module: str
    channel: int = Field(ge=0, le=125)
    data_rate: str
    glove_to_gateway_pipe: str
    gateway_to_glove_pipe: str
    packet_sequence_required: bool = True


class VoiceSettings(BaseModel):
    enabled: bool = True
    stt_backend: str
    tts_backend: str
    barge_in: bool = True


class CognitionSettings(BaseModel):
    structured_output_required: bool = True
    allow_freeform_motion_commands: bool = False
    session_memory: bool = True


class AppSettings(BaseModel):
    system: SystemSettings
    safety: SafetySettings
    robot: RobotSettings
    servos: ServosSettings
    imu: IMUSettings
    radio: RadioSettings
    voice: VoiceSettings
    cognition: CognitionSettings
