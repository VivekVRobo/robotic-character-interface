from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from rci.config.loader import ConfigLoader
from rci.hil.gate import HilGateReason, SingleServoHilGate
from rci.hil.models import (
    ElectricalEvidence,
    EvidenceKind,
    EvidenceReference,
    MechanicalEvidence,
    ServoCalibrationEvidence,
    SingleServoHilEvidence,
    evidence_digest,
)


_HASH_A = "a" * 64
_HASH_B = "b" * 64


def _calibration(**overrides: object) -> ServoCalibrationEvidence:
    values: dict[str, object] = {
        "joint_name": "base",
        "servo_model": "measured-test-servo",
        "driver": "PCA9685",
        "pwm_frequency_hz": 50.0,
        "channel": 0,
        "protocol_id": 1,
        "lower_angle_deg": -60.0,
        "neutral_angle_deg": 0.0,
        "upper_angle_deg": 60.0,
        "lower_pulse_us": 1100,
        "neutral_pulse_us": 1500,
        "upper_pulse_us": 1900,
        "test_lower_angle_deg": -10.0,
        "test_upper_angle_deg": 10.0,
        "max_test_step_deg": 2.0,
    }
    values.update(overrides)
    return ServoCalibrationEvidence.model_validate(values)


def _evidence(
    *,
    calibration: ServoCalibrationEvidence | None = None,
    electrical: ElectricalEvidence | None = None,
    mechanical: MechanicalEvidence | None = None,
) -> SingleServoHilEvidence:
    return SingleServoHilEvidence(
        recorded_at=datetime(2026, 9, 2, tzinfo=UTC),
        operator="test-operator",
        calibration=_calibration() if calibration is None else calibration,
        electrical=(
            ElectricalEvidence(
                actuator_supply_voltage_v=6.0,
                logic_supply_voltage_v=5.0,
                current_limit_a=1.0,
                common_ground_verified=True,
                actuator_logic_rails_separate=True,
                independent_estop_verified=True,
                power_cut_verified=True,
            )
            if electrical is None
            else electrical
        ),
        mechanical=(
            MechanicalEvidence(
                servo_secured=True,
                load_path_clear=True,
                manual_range_check_verified=True,
                hard_stop_clearance_verified=True,
            )
            if mechanical is None
            else mechanical
        ),
        evidence_refs=(
            EvidenceReference(kind=EvidenceKind.WIRING, uri="evidence/wiring.png", sha256=_HASH_A),
            EvidenceReference(
                kind=EvidenceKind.MEASUREMENT,
                uri="evidence/calibration.csv",
                sha256=_HASH_B,
            ),
        ),
    )


def test_complete_measured_evidence_mints_single_joint_permit_without_global_verification() -> None:
    settings = ConfigLoader().load()
    assert not settings.servos.hardware_verified

    evidence = _evidence()
    decision = SingleServoHilGate(settings).evaluate(evidence)

    assert decision.approved
    assert decision.reasons == ()
    assert decision.permit is not None
    assert decision.permit.joint_name == "base"
    assert decision.permit.channel == 0
    assert decision.permit.protocol_id == 1
    assert decision.permit.test_lower_angle_deg == -10.0
    assert decision.permit.test_upper_angle_deg == 10.0
    assert decision.permit.evidence_sha256 == evidence_digest(evidence)
    assert not settings.servos.hardware_verified


def test_missing_physical_checks_fail_closed_with_machine_readable_reasons() -> None:
    settings = ConfigLoader().load()
    evidence = _evidence(
        electrical=ElectricalEvidence(
            actuator_supply_voltage_v=6.0,
            logic_supply_voltage_v=5.0,
            current_limit_a=1.0,
        ),
        mechanical=MechanicalEvidence(),
    )

    decision = SingleServoHilGate(settings).evaluate(evidence)

    assert not decision.approved
    assert decision.permit is None
    assert set(decision.reasons) == {
        HilGateReason.COMMON_GROUND_UNVERIFIED,
        HilGateReason.ACTUATOR_LOGIC_RAILS_NOT_SEPARATE,
        HilGateReason.INDEPENDENT_ESTOP_UNVERIFIED,
        HilGateReason.POWER_CUT_UNVERIFIED,
        HilGateReason.SERVO_NOT_SECURED,
        HilGateReason.LOAD_PATH_NOT_CLEAR,
        HilGateReason.MANUAL_RANGE_UNVERIFIED,
        HilGateReason.HARD_STOP_CLEARANCE_UNVERIFIED,
    }


def test_config_identity_mismatch_cannot_mint_permit() -> None:
    settings = ConfigLoader().load()
    evidence = _evidence(calibration=_calibration(channel=7, protocol_id=9, driver="other"))

    decision = SingleServoHilGate(settings).evaluate(evidence)

    assert not decision.approved
    assert decision.permit is None
    assert HilGateReason.CONFIG_CHANNEL_MISMATCH in decision.reasons
    assert HilGateReason.CONFIG_PROTOCOL_ID_MISMATCH in decision.reasons
    assert HilGateReason.CONFIG_DRIVER_MISMATCH in decision.reasons


def test_invalid_measured_calibration_is_rejected_before_activation_gate() -> None:
    with pytest.raises(ValidationError, match="lower < neutral < upper"):
        _calibration(lower_angle_deg=10.0, neutral_angle_deg=0.0, upper_angle_deg=60.0)

    with pytest.raises(ValidationError, match="neutral pulse"):
        _calibration(lower_pulse_us=1100, neutral_pulse_us=2100, upper_pulse_us=1900)


def test_wiring_and_measurement_artifacts_are_both_mandatory() -> None:
    with pytest.raises(ValidationError, match="wiring artifact"):
        SingleServoHilEvidence(
            recorded_at=datetime(2026, 9, 2, tzinfo=UTC),
            operator="test-operator",
            calibration=_calibration(),
            electrical=_evidence().electrical,
            mechanical=_evidence().mechanical,
            evidence_refs=(
                EvidenceReference(
                    kind=EvidenceKind.MEASUREMENT,
                    uri="evidence/calibration.csv",
                    sha256=_HASH_B,
                ),
                EvidenceReference(
                    kind=EvidenceKind.PHOTO,
                    uri="evidence/setup.png",
                    sha256=_HASH_A,
                ),
            ),
        )


def test_evidence_digest_changes_when_measured_values_change() -> None:
    first = _evidence()
    second = _evidence(calibration=_calibration(max_test_step_deg=1.0))
    assert evidence_digest(first) != evidence_digest(second)
