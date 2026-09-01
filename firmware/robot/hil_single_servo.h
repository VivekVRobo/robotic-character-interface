#pragma once

#include <stdint.h>

namespace rci {
namespace robot {

struct SingleServoHilCalibration {
  uint8_t protocol_id = 0u;
  uint8_t channel = 0u;
  int16_t lower_cdeg = 0;
  int16_t neutral_cdeg = 0;
  int16_t upper_cdeg = 0;
  uint16_t lower_pulse_us = 0u;
  uint16_t neutral_pulse_us = 0u;
  uint16_t upper_pulse_us = 0u;
  int16_t test_lower_cdeg = 0;
  int16_t test_upper_cdeg = 0;
  uint16_t max_step_cdeg = 0u;
};

enum class HilGuardDecision : uint8_t {
  kRejectedUnconfigured = 0,
  kRejectedNotArmed = 1,
  kRejectedJointMismatch = 2,
  kRejectedOutsideTestEnvelope = 3,
  kRejectedStepTooLarge = 4,
  kEligibleForDriverLayer = 5,
};

inline bool ValidHilCalibration(const SingleServoHilCalibration& calibration) {
  if (calibration.protocol_id == 0u || calibration.max_step_cdeg == 0u) {
    return false;
  }
  if (!(calibration.lower_cdeg < calibration.neutral_cdeg &&
        calibration.neutral_cdeg < calibration.upper_cdeg)) {
    return false;
  }
  if (!(calibration.lower_cdeg <= calibration.test_lower_cdeg &&
        calibration.test_lower_cdeg < calibration.test_upper_cdeg &&
        calibration.test_upper_cdeg <= calibration.upper_cdeg)) {
    return false;
  }
  if (!(calibration.test_lower_cdeg <= calibration.neutral_cdeg &&
        calibration.neutral_cdeg <= calibration.test_upper_cdeg)) {
    return false;
  }
  if (calibration.lower_pulse_us == 0u || calibration.neutral_pulse_us == 0u ||
      calibration.upper_pulse_us == 0u ||
      calibration.lower_pulse_us == calibration.upper_pulse_us) {
    return false;
  }

  const uint16_t pulse_low = calibration.lower_pulse_us < calibration.upper_pulse_us
                                 ? calibration.lower_pulse_us
                                 : calibration.upper_pulse_us;
  const uint16_t pulse_high = calibration.lower_pulse_us > calibration.upper_pulse_us
                                  ? calibration.lower_pulse_us
                                  : calibration.upper_pulse_us;
  if (!(pulse_low < calibration.neutral_pulse_us &&
        calibration.neutral_pulse_us < pulse_high)) {
    return false;
  }

  const uint16_t test_span = static_cast<uint16_t>(
      calibration.test_upper_cdeg - calibration.test_lower_cdeg);
  return calibration.max_step_cdeg <= test_span;
}

class SingleServoHilGuard {
 public:
  bool Configure(const SingleServoHilCalibration& calibration) {
    if (!ValidHilCalibration(calibration)) {
      configured_ = false;
      armed_ = false;
      return false;
    }
    calibration_ = calibration;
    configured_ = true;
    armed_ = false;
    estop_latched_ = false;
    return true;
  }

  bool Arm(bool wiring_verified, bool independent_estop_verified, bool estop_clear,
           bool manual_acknowledgement) {
    if (!configured_ || !wiring_verified || !independent_estop_verified ||
        !estop_clear || !manual_acknowledgement || estop_latched_) {
      armed_ = false;
      return false;
    }
    armed_ = true;
    return true;
  }

  void ObserveEstop(bool active) {
    if (active) {
      estop_latched_ = true;
      armed_ = false;
    }
  }

  bool ManualReset(bool estop_clear, bool manual_acknowledgement) {
    if (!configured_ || !estop_clear || !manual_acknowledgement) {
      return false;
    }
    estop_latched_ = false;
    armed_ = false;
    return true;
  }

  HilGuardDecision EvaluateTarget(uint8_t protocol_id, int16_t current_cdeg,
                                  int16_t target_cdeg) const {
    if (!configured_) {
      return HilGuardDecision::kRejectedUnconfigured;
    }
    if (!armed_ || estop_latched_) {
      return HilGuardDecision::kRejectedNotArmed;
    }
    if (protocol_id != calibration_.protocol_id) {
      return HilGuardDecision::kRejectedJointMismatch;
    }
    if (target_cdeg < calibration_.test_lower_cdeg ||
        target_cdeg > calibration_.test_upper_cdeg) {
      return HilGuardDecision::kRejectedOutsideTestEnvelope;
    }

    const int32_t delta = static_cast<int32_t>(target_cdeg) - current_cdeg;
    const uint32_t magnitude = static_cast<uint32_t>(delta < 0 ? -delta : delta);
    if (magnitude > calibration_.max_step_cdeg) {
      return HilGuardDecision::kRejectedStepTooLarge;
    }
    return HilGuardDecision::kEligibleForDriverLayer;
  }

  bool configured() const { return configured_; }
  bool armed() const { return armed_; }
  bool estop_latched() const { return estop_latched_; }

 private:
  SingleServoHilCalibration calibration_{};
  bool configured_ = false;
  bool armed_ = false;
  bool estop_latched_ = false;
};

}  // namespace robot
}  // namespace rci
