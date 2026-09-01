#pragma once

#include <stddef.h>
#include <stdint.h>

#include "../shared/protocol.h"

namespace rci {
namespace robot {

constexpr uint32_t kDefaultHeartbeatTimeoutMs = 500u;

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

class RobotRuntime {
 public:
  explicit RobotRuntime(uint32_t heartbeat_timeout_ms = kDefaultHeartbeatTimeoutMs)
      : heartbeat_timeout_ms_(heartbeat_timeout_ms) {}

  RuntimeState state() const { return state_; }
  bool physical_estop_active() const { return physical_estop_active_; }
  bool heartbeat_seen() const { return heartbeat_seen_; }
  bool heartbeat_healthy() const { return heartbeat_healthy_; }
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
        Tick(now_ms);
        if (state_ != RuntimeState::kReady || !heartbeat_healthy_ ||
            physical_estop_active_) {
          return DispatchResult::kMotionRejectedUnsafe;
        }
        // PR-012 intentionally has no actuator layer. A validated command can
        // reach this boundary, but execution remains deferred until later HIL.
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
  RuntimeState state_ = RuntimeState::kSafe;
  bool physical_estop_active_ = false;
  bool heartbeat_seen_ = false;
  bool heartbeat_healthy_ = false;
  uint16_t last_sequence_ = 0;
  uint32_t last_heartbeat_ms_ = 0;
  uint32_t heartbeat_timeout_ms_;
};

}  // namespace robot
}  // namespace rci
