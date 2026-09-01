#include <assert.h>
#include <stddef.h>
#include <stdint.h>

#include "../../firmware/robot/runtime.h"

namespace {

using rci::protocol::BuildFrame;
using rci::protocol::MessageType;
using rci::robot::DispatchResult;
using rci::robot::RobotRuntime;
using rci::robot::RuntimeState;

size_t Build(MessageType type, uint16_t sequence, uint8_t* out, size_t capacity) {
  return BuildFrame(type, sequence, nullptr, 0, out, capacity);
}

void TestStartsFailClosedAndHeartbeatArmsRuntime() {
  RobotRuntime runtime(500);
  uint8_t frame[32] = {};

  assert(runtime.state() == RuntimeState::kSafe);
  assert(!runtime.heartbeat_healthy());

  size_t size = Build(MessageType::kValidatedMotionCommand, 1, frame, sizeof(frame));
  assert(size > 0);
  assert(runtime.HandleFrame(frame, size, 0) == DispatchResult::kMotionRejectedUnsafe);

  size = Build(MessageType::kHeartbeat, 2, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 10) == DispatchResult::kHeartbeatAccepted);
  assert(runtime.state() == RuntimeState::kReady);
  assert(runtime.heartbeat_healthy());

  size = Build(MessageType::kValidatedMotionCommand, 3, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 20) == DispatchResult::kMotionDeferred);
  assert(runtime.state() == RuntimeState::kReady);
}

void TestHeartbeatTimeoutReturnsToSafe() {
  RobotRuntime runtime(500);
  uint8_t frame[32] = {};
  size_t size = Build(MessageType::kHeartbeat, 1, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);

  runtime.Tick(600);
  assert(runtime.state() == RuntimeState::kReady);
  runtime.Tick(601);
  assert(runtime.state() == RuntimeState::kSafe);
  assert(!runtime.heartbeat_healthy());

  size = Build(MessageType::kValidatedMotionCommand, 2, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 601) == DispatchResult::kMotionRejectedUnsafe);
}

void TestSoftwareEstopIsStickyUntilManualReset() {
  RobotRuntime runtime(500);
  uint8_t frame[32] = {};
  size_t size = Build(MessageType::kHeartbeat, 1, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);

  size = Build(MessageType::kEstop, 2, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 110) == DispatchResult::kEstopLatched);
  assert(runtime.state() == RuntimeState::kEstop);

  size = Build(MessageType::kHeartbeat, 3, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 120) == DispatchResult::kHeartbeatAccepted);
  assert(runtime.state() == RuntimeState::kEstop);
  assert(runtime.ManualReset(120));
  assert(runtime.state() == RuntimeState::kReady);
}

void TestPhysicalEstopBlocksReset() {
  RobotRuntime runtime(500);
  uint8_t frame[32] = {};
  size_t size = Build(MessageType::kHeartbeat, 1, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);

  runtime.ObservePhysicalEstop(true);
  assert(runtime.state() == RuntimeState::kEstop);
  assert(!runtime.ManualReset(110));

  runtime.ObservePhysicalEstop(false);
  assert(runtime.state() == RuntimeState::kEstop);
  assert(runtime.ManualReset(120));
  assert(runtime.state() == RuntimeState::kReady);
}

void TestInvalidFrameNeverChangesSafetyState() {
  RobotRuntime runtime(500);
  uint8_t frame[32] = {};
  size_t size = Build(MessageType::kHeartbeat, 7, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);
  assert(runtime.state() == RuntimeState::kReady);

  frame[size - 1] ^= 0x01u;
  assert(runtime.HandleFrame(frame, size, 110) == DispatchResult::kRejectedInvalidFrame);
  assert(runtime.state() == RuntimeState::kReady);
  assert(runtime.last_sequence() == 7);
}

}  // namespace

int main() {
  TestStartsFailClosedAndHeartbeatArmsRuntime();
  TestHeartbeatTimeoutReturnsToSafe();
  TestSoftwareEstopIsStickyUntilManualReset();
  TestPhysicalEstopBlocksReset();
  TestInvalidFrameNeverChangesSafetyState();
  return 0;
}
