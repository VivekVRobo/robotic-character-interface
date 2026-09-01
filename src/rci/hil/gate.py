"""Fail-closed readiness gate for the first physical single-servo HIL attempt."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from rci.config.models import AppSettings
from rci.hil.models import HilActivationPermit, SingleServoHilEvidence, evidence_digest


class HilGateReason(StrEnum):
    CONFIG_JOINT_MISSING = "config_joint_missing"
    CONFIG_PROTOCOL_ID_MISSING = "config_protocol_id_missing"
    CONFIG_PROTOCOL_ID_MISMATCH = "config_protocol_id_mismatch"
    CONFIG_CHANNEL_MISMATCH = "config_channel_mismatch"
    CONFIG_DRIVER_MISMATCH = "config_driver_mismatch"
    CONFIG_PWM_FREQUENCY_MISMATCH = "config_pwm_frequency_mismatch"
    COMMON_GROUND_UNVERIFIED = "common_ground_unverified"
    ACTUATOR_LOGIC_RAILS_NOT_SEPARATE = "actuator_logic_rails_not_separate"
    INDEPENDENT_ESTOP_UNVERIFIED = "independent_estop_unverified"
    POWER_CUT_UNVERIFIED = "power_cut_unverified"
    SERVO_NOT_SECURED = "servo_not_secured"
    LOAD_PATH_NOT_CLEAR = "load_path_not_clear"
    MANUAL_RANGE_UNVERIFIED = "manual_range_unverified"
    HARD_STOP_CLEARANCE_UNVERIFIED = "hard_stop_clearance_unverified"


class HilGateDecision(BaseModel):
    """Immutable readiness result; a permit exists only on complete approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: bool
    reasons: tuple[HilGateReason, ...]
    permit: HilActivationPermit | None = None


class SingleServoHilGate:
    """Validate measured evidence against canonical software identity and wiring config."""

    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    def evaluate(self, evidence: SingleServoHilEvidence) -> HilGateDecision:
        calibration = evidence.calibration
        reasons: list[HilGateReason] = []
        configured_joint = self._settings.servos.joints.get(calibration.joint_name)

        if configured_joint is None:
            reasons.append(HilGateReason.CONFIG_JOINT_MISSING)
        else:
            if configured_joint.protocol_id is None:
                reasons.append(HilGateReason.CONFIG_PROTOCOL_ID_MISSING)
            elif configured_joint.protocol_id != calibration.protocol_id:
                reasons.append(HilGateReason.CONFIG_PROTOCOL_ID_MISMATCH)
            if configured_joint.channel != calibration.channel:
                reasons.append(HilGateReason.CONFIG_CHANNEL_MISMATCH)

        if self._settings.servos.driver != calibration.driver:
            reasons.append(HilGateReason.CONFIG_DRIVER_MISMATCH)
        if self._settings.servos.pwm_frequency_hz != calibration.pwm_frequency_hz:
            reasons.append(HilGateReason.CONFIG_PWM_FREQUENCY_MISMATCH)

        electrical = evidence.electrical
        if not electrical.common_ground_verified:
            reasons.append(HilGateReason.COMMON_GROUND_UNVERIFIED)
        if not electrical.actuator_logic_rails_separate:
            reasons.append(HilGateReason.ACTUATOR_LOGIC_RAILS_NOT_SEPARATE)
        if not electrical.independent_estop_verified:
            reasons.append(HilGateReason.INDEPENDENT_ESTOP_UNVERIFIED)
        if not electrical.power_cut_verified:
            reasons.append(HilGateReason.POWER_CUT_UNVERIFIED)

        mechanical = evidence.mechanical
        if not mechanical.servo_secured:
            reasons.append(HilGateReason.SERVO_NOT_SECURED)
        if not mechanical.load_path_clear:
            reasons.append(HilGateReason.LOAD_PATH_NOT_CLEAR)
        if not mechanical.manual_range_check_verified:
            reasons.append(HilGateReason.MANUAL_RANGE_UNVERIFIED)
        if not mechanical.hard_stop_clearance_verified:
            reasons.append(HilGateReason.HARD_STOP_CLEARANCE_UNVERIFIED)

        if reasons:
            return HilGateDecision(approved=False, reasons=tuple(reasons))

        permit = HilActivationPermit(
            evidence_sha256=evidence_digest(evidence),
            joint_name=calibration.joint_name,
            channel=calibration.channel,
            protocol_id=calibration.protocol_id,
            lower_angle_deg=calibration.lower_angle_deg,
            neutral_angle_deg=calibration.neutral_angle_deg,
            upper_angle_deg=calibration.upper_angle_deg,
            lower_pulse_us=calibration.lower_pulse_us,
            neutral_pulse_us=calibration.neutral_pulse_us,
            upper_pulse_us=calibration.upper_pulse_us,
            test_lower_angle_deg=calibration.test_lower_angle_deg,
            test_upper_angle_deg=calibration.test_upper_angle_deg,
            max_test_step_deg=calibration.max_test_step_deg,
        )
        return HilGateDecision(approved=True, reasons=(), permit=permit)
