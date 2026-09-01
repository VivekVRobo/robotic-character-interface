#pragma once

#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "../shared/protocol.h"

namespace rci {
namespace robot {

constexpr uint32_t kDefaultHeartbeatTimeoutMs = 500u;
constexpr uint8_t kPositionMotionMode = 0x01u;
constexpr uint8_t kMaxJointTargets = 8u;
constexpr size_t kMotionCommandIdSize = 16u;
constexpr size_t kMotionFixedPayloadSize = 16u + 4u + 4u;
constexpr size_t kJointTargetPayloadSize = 3u;

enum class RuntimeState : uint8_t {
  kSafe = 0,
  kReady = 1,
  kEstop = 2,
};

enum class DispatchResult : uint8_t {
  kRejectedInvalidFrame = 0,
  kHeartbeatAccepted = 1,
  kEstopLatched = 2,
  kMotionDeferred = 3,
  kMotionRejectedUnsafe = 4,
  kMessageIgnored = 5,
  kMotionRejectedInvalidPayload = 6,
  kRejectedReplay = 7,
};

struct ParsedFrame {
  protocol::MessageType type;
  uint16_t sequence;
  const uint8_t* payload;
  uint16_t payload_length;
};

inline uint16_t ReadU16Le(const uint8_t* data) {
  return static_cast<uint16_t>(data[0]) |
         static_cast<uint16_t>(static_cast<uint16_t>(data[1]) << 8);
}

inline bool ParseFrame(const uint8_t* data, size_t length, ParsedFrame* out) {
  if (data == nullptr || out == nullptr || length < protocol::kFrameOverhead) {
    return false;
  }
  if (data[0] != protocol::kMagic0 || data[1] != protocol::kMagic1 ||
      data[2] != kProtocolVersion) {
    return false;
  }

  const uint16_t payload_length = ReadU16Le(data + 6);
  if (payload_length > protocol::kMaxPayloadSize) {
    return false;
  }
  const size_t expected_length = protocol::kFrameOverhead + payload_length;
  if (length != expected_length) {
    return false;
  }

  const uint16_t expected_crc = ReadU16Le(data + protocol::kHeaderSize + payload_length);
  const uint16_t actual_crc =
      protocol::Crc16CcittFalse(data, protocol::kHeaderSize + payload_length);
  if (expected_crc != actual_crc) {
    return false;
  }

  switch (static_cast<protocol::MessageType>(data[3])) {
    case protocol::MessageType::kGloveTelemetry:
    case protocol::MessageType::kHeartbeat:
    case protocol::MessageType::kValidatedMotionCommand:
    case protocol::MessageType::kEstop:
    case protocol::MessageType::kAck:
    case protocol::MessageType::kNack:
    case protocol::MessageType::kRobotTelemetry:
      break;
    default:
      return false;
  }

  out->type = static_cast<protocol::MessageType>(data[3]);
  out->sequence = ReadU16Le(data + 4);
  out->payload = data + protocol::kHeaderSize;
  out->payload_length = payload_length;
  return true;
}

inline bool ValidateMotionPayload(const uint8_t* payload, uint16_t payload_length) {
  if (payload == nullptr || payload_length < kMotionFixedPayloadSize + kJointTargetPayloadSize) {
    return false;
  }

  const uint16_t ttl_ms = ReadU16Le(payload + 16);
  const uint8_t mode = payload[18];
  const uint8_t joint_count = payload[19];
  if (ttl_ms == 0u || mode != kPositionMotionMode || joint_count == 0u ||
      joint_count > kMaxJointTargets) {
    return false;
  }

  const size_t expected_size = kMotionFixedPayloadSize +
                               static_cast<size_t>(joint_count) * kJointTargetPayloadSize;
  if (payload_length != expected_size) {
    return false;
  }

  bool seen_joint_ids[256] = {};
  size_t offset = 20u;
  for (uint8_t i = 0; i < joint_count; ++i) {
    const uint8_t joint_id = payload[offset];
    if (joint_id == 0u || seen_joint_ids[joint_id]) {
      return false;
    }
    seen_joint_ids[joint_id] = true;
    offset += kJointTargetPayloadSize;
  }

  const uint16_t max_velocity = ReadU16Le(payload + offset);
  const uint16_t max_acceleration = ReadU16Le(payload + offset + 2u);
  return max_velocity > 0u && max_acceleration > 0u;
}

inline bool SequenceIsFresh(uint16_t candidate, uint16_t previous) {
  const uint16_t delta = static_cast<uint16_t>(candidate - previous);
  return delta != 0u && delta < 0x8000u;
}

inline protocol::AckStatus AckStatusForDispatch(DispatchResult result) {
  switch (result) {
    case DispatchResult::kHeartbeatAccepted:
    case DispatchResult::kEstopLatched:
    case DispatchResult::kMotionDeferred:
      return protocol::AckStatus::kOk;
    case DispatchResult::kMotionRejectedUnsafe:
      return protocol::AckStatus::kRejected;
    case DispatchResult::kRejectedReplay:
      return protocol::AckStatus::kStale;
    case DispatchResult::kMotionRejectedInvalidPayload:
    case DispatchResult::kMessageIgnored:
    case DispatchResult::kRejectedInvalidFrame:
      return protocol::AckStatus::kInvalid;
  }
  return protocol::AckStatus::kInvalid;
}

class RobotRuntime {
 public:
  explicit RobotRuntime(uint32_t heartbeat_timeout_ms = kDefaultHeartbeatTimeoutMs)
      : heartbeat_timeout_ms_(heartbeat_timeout_ms) {}

  RuntimeState state() const { return state_; }
  bool physical_estop_active() const { return physical_estop_active_; }
  bool heartbeat_seen() const { return heartbeat_seen_; }
  bool heartbeat_healthy() const { return heartbeat_healthy_; }
  bool sequence_seen() const { return sequence_seen_; }
  uint16_t last_sequence() const { return last_sequence_; }

  void ObservePhysicalEstop(bool active) {
    physical_estop_active_ = active;
    if (active) {
      state_ = RuntimeState::kEstop;
    }
  }

  void Tick(uint32_t now_ms) {
    if (!heartbeat_seen_) {
      heartbeat_healthy_ = false;
      if (state_ == RuntimeState::kReady) {
        state_ = RuntimeState::kSafe;
      }
      return;
    }

    const uint32_t age_ms = now_ms - last_heartbeat_ms_;
    heartbeat_healthy_ = age_ms <= heartbeat_timeout_ms_;
    if (!heartbeat_healthy_ && state_ != RuntimeState::kEstop) {
      state_ = RuntimeState::kSafe;
    }
  }

  DispatchResult HandleFrame(const uint8_t* data, size_t length, uint32_t now_ms) {
    ParsedFrame frame{};
    if (!ParseFrame(data, length, &frame)) {
      return DispatchResult::kRejectedInvalidFrame;
    }
    if (sequence_seen_ && !SequenceIsFresh(frame.sequence, last_sequence_)) {
      return DispatchResult::kRejectedReplay;
    }

    sequence_seen_ = true;
    last_sequence_ = frame.sequence;
    switch (frame.type) {
      case protocol::MessageType::kHeartbeat:
        last_heartbeat_ms_ = now_ms;
        heartbeat_seen_ = true;
        heartbeat_healthy_ = true;
        if (state_ == RuntimeState::kSafe && !physical_estop_active_) {
          state_ = RuntimeState::kReady;
        }
        return DispatchResult::kHeartbeatAccepted;

      case protocol::MessageType::kEstop:
        state_ = RuntimeState::kEstop;
        return DispatchResult::kEstopLatched;

      case protocol::MessageType::kValidatedMotionCommand:
        if (!ValidateMotionPayload(frame.payload, frame.payload_length)) {
          return DispatchResult::kMotionRejectedInvalidPayload;
        }
        Tick(now_ms);
        if (state_ != RuntimeState::kReady || !heartbeat_healthy_ ||
            physical_estop_active_) {
          return DispatchResult::kMotionRejectedUnsafe;
        }
        if (MotionCommandWasAccepted(frame.payload)) {
          return DispatchResult::kRejectedReplay;
        }
        RememberMotionCommand(frame.payload);
        // The payload is structurally valid and the independent watchdog is
        // healthy, but there is still no actuator layer. Execution remains
        // deferred until explicit HIL and firmware-side joint safety exist.
        return DispatchResult::kMotionDeferred;

      default:
        return DispatchResult::kMessageIgnored;
    }
  }

  bool ManualReset(uint32_t now_ms) {
    Tick(now_ms);
    if (physical_estop_active_ || !heartbeat_healthy_) {
      return false;
    }
    state_ = RuntimeState::kReady;
    return true;
  }

 private:
  bool MotionCommandWasAccepted(const uint8_t* payload) const {
    return motion_command_seen_ &&
           memcmp(last_motion_command_id_, payload, kMotionCommandIdSize) == 0;
  }

  void RememberMotionCommand(const uint8_t* payload) {
    memcpy(last_motion_command_id_, payload, kMotionCommandIdSize);
    motion_command_seen_ = true;
  }

  RuntimeState state_ = RuntimeState::kSafe;
  bool physical_estop_active_ = false;
  bool heartbeat_seen_ = false;
  bool heartbeat_healthy_ = false;
  bool sequence_seen_ = false;
  bool motion_command_seen_ = false;
  uint16_t last_sequence_ = 0;
  uint8_t last_motion_command_id_[kMotionCommandIdSize] = {};
  uint32_t last_heartbeat_ms_ = 0;
  uint32_t heartbeat_timeout_ms_;
};

}  // namespace robot
}  // namespace rci
