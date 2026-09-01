#include <assert.h>
#include <stddef.h>
#include <stdint.h>

#include "../../firmware/robot/runtime.h"

namespace {

using rci::protocol::AckStatus;
using rci::protocol::BuildFrame;
using rci::protocol::MessageType;
using rci::protocol::WriteU16Le;
using rci::robot::AckStatusForDispatch;
using rci::robot::DispatchResult;
using rci::robot::RobotRuntime;
using rci::robot::RuntimeState;

size_t Build(MessageType type, uint16_t sequence, uint8_t* out, size_t capacity) {
  return BuildFrame(type, sequence, nullptr, 0, out, capacity);
}

size_t BuildValidMotion(uint16_t sequence, uint8_t* out, size_t capacity) {
  uint8_t payload[27] = {};
  WriteU16Le(payload + 16, 250);
  payload[18] = 1;
  payload[19] = 1;
  payload[20] = 1;
  WriteU16Le(payload + 21, 0);
  WriteU16Le(payload + 23, 6000);
  WriteU16Le(payload + 25, 18000);
  return BuildFrame(
      MessageType::kValidatedMotionCommand,
      sequence,
      payload,
      sizeof(payload),
      out,
      capacity);
}

void TestStartsFailClosedAndHeartbeatArmsRuntime() {
  RobotRuntime runtime(500);
  uint8_t frame[64] = {};

  assert(runtime.state() == RuntimeState::kSafe);
  assert(!runtime.heartbeat_healthy());

  size_t size = BuildValidMotion(1, frame, sizeof(frame));
  assert(size > 0);
  assert(runtime.HandleFrame(frame, size, 0) == DispatchResult::kMotionRejectedUnsafe);

  size = Build(MessageType::kHeartbeat, 2, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 10) == DispatchResult::kHeartbeatAccepted);
  assert(runtime.state() == RuntimeState::kReady);
  assert(runtime.heartbeat_healthy());

  size = BuildValidMotion(3, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 20) == DispatchResult::kMotionDeferred);
  assert(runtime.state() == RuntimeState::kReady);
}

void TestHeartbeatTimeoutReturnsToSafe() {
  RobotRuntime runtime(500);
  uint8_t frame[64] = {};
  size_t size = Build(MessageType::kHeartbeat, 1, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);

  runtime.Tick(600);
  assert(runtime.state() == RuntimeState::kReady);
  runtime.Tick(601);
  assert(runtime.state() == RuntimeState::kSafe);
  assert(!runtime.heartbeat_healthy());

  size = BuildValidMotion(2, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 601) == DispatchResult::kMotionRejectedUnsafe);
}

void TestSoftwareEstopIsStickyUntilManualReset() {
  RobotRuntime runtime(500);
  uint8_t frame[64] = {};
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
  uint8_t frame[64] = {};
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
  uint8_t frame[64] = {};
  size_t size = Build(MessageType::kHeartbeat, 7, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);
  assert(runtime.state() == RuntimeState::kReady);

  frame[size - 1] ^= 0x01u;
  assert(runtime.HandleFrame(frame, size, 110) == DispatchResult::kRejectedInvalidFrame);
  assert(runtime.state() == RuntimeState::kReady);
  assert(runtime.last_sequence() == 7);
}

void TestMalformedMotionPayloadIsInvalidNotDeferred() {
  RobotRuntime runtime(500);
  uint8_t frame[64] = {};
  size_t size = Build(MessageType::kHeartbeat, 1, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 100) == DispatchResult::kHeartbeatAccepted);

  size = Build(MessageType::kValidatedMotionCommand, 2, frame, sizeof(frame));
  assert(runtime.HandleFrame(frame, size, 110) ==
         DispatchResult::kMotionRejectedInvalidPayload);
  assert(runtime.state() == RuntimeState::kReady);
}

void TestDispatchResultsMapToExplicitAckStatus() {
  assert(AckStatusForDispatch(DispatchResult::kHeartbeatAccepted) == AckStatus::kOk);
  assert(AckStatusForDispatch(DispatchResult::kEstopLatched) == AckStatus::kOk);
  assert(AckStatusForDispatch(DispatchResult::kMotionDeferred) == AckStatus::kOk);
  assert(AckStatusForDispatch(DispatchResult::kMotionRejectedUnsafe) ==
         AckStatus::kRejected);
  assert(AckStatusForDispatch(DispatchResult::kMotionRejectedInvalidPayload) ==
         AckStatus::kInvalid);
}

}  // namespace

int main() {
  TestStartsFailClosedAndHeartbeatArmsRuntime();
  TestHeartbeatTimeoutReturnsToSafe();
  TestSoftwareEstopIsStickyUntilManualReset();
  TestPhysicalEstopBlocksReset();
  TestInvalidFrameNeverChangesSafetyState();
  TestMalformedMotionPayloadIsInvalidNotDeferred();
  TestDispatchResultsMapToExplicitAckStatus();
  return 0;
}
