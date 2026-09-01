#include <assert.h>
#include <stdint.h>

#include "../../firmware/robot/hil_single_servo.h"

namespace {

using rci::robot::HilGuardDecision;
using rci::robot::SingleServoHilCalibration;
using rci::robot::SingleServoHilGuard;

SingleServoHilCalibration ValidCalibration() {
  SingleServoHilCalibration calibration{};
  calibration.protocol_id = 1u;
  calibration.channel = 0u;
  calibration.lower_cdeg = -6000;
  calibration.neutral_cdeg = 0;
  calibration.upper_cdeg = 6000;
  calibration.lower_pulse_us = 1100u;
  calibration.neutral_pulse_us = 1500u;
  calibration.upper_pulse_us = 1900u;
  calibration.test_lower_cdeg = -1000;
  calibration.test_upper_cdeg = 1000;
  calibration.max_step_cdeg = 200u;
  return calibration;
}

void TestCannotArmWithoutCompletePhysicalChecks() {
  SingleServoHilGuard guard;
  assert(guard.Configure(ValidCalibration()));
  assert(!guard.Arm(false, true, true, true));
  assert(!guard.Arm(true, false, true, true));
  assert(!guard.Arm(true, true, false, true));
  assert(!guard.Arm(true, true, true, false));
  assert(!guard.armed());
}

void TestNarrowEnvelopeAndStepLimitAreAuthoritative() {
  SingleServoHilGuard guard;
  assert(guard.Configure(ValidCalibration()));
  assert(guard.Arm(true, true, true, true));

  assert(guard.EvaluateTarget(1u, 0, 100) == HilGuardDecision::kEligibleForDriverLayer);
  assert(guard.EvaluateTarget(2u, 0, 100) == HilGuardDecision::kRejectedJointMismatch);
  assert(guard.EvaluateTarget(1u, 0, 1100) ==
         HilGuardDecision::kRejectedOutsideTestEnvelope);
  assert(guard.EvaluateTarget(1u, 0, 300) == HilGuardDecision::kRejectedStepTooLarge);
}

void TestEstopDisarmsAndRequiresManualResetThenRearm() {
  SingleServoHilGuard guard;
  assert(guard.Configure(ValidCalibration()));
  assert(guard.Arm(true, true, true, true));

  guard.ObserveEstop(true);
  assert(guard.estop_latched());
  assert(!guard.armed());
  assert(guard.EvaluateTarget(1u, 0, 100) == HilGuardDecision::kRejectedNotArmed);
  assert(!guard.Arm(true, true, true, true));

  assert(guard.ManualReset(true, true));
  assert(!guard.estop_latched());
  assert(!guard.armed());
  assert(guard.Arm(true, true, true, true));
}

void TestInvalidCalibrationNeverConfigures() {
  SingleServoHilGuard guard;
  auto calibration = ValidCalibration();
  calibration.neutral_pulse_us = 2500u;
  assert(!guard.Configure(calibration));
  assert(!guard.configured());
  assert(guard.EvaluateTarget(1u, 0, 100) == HilGuardDecision::kRejectedUnconfigured);
}

}  // namespace

int main() {
  TestCannotArmWithoutCompletePhysicalChecks();
  TestNarrowEnvelopeAndStepLimitAreAuthoritative();
  TestEstopDisarmsAndRequiresManualResetThenRearm();
  TestInvalidCalibrationNeverConfigures();
  return 0;
}
