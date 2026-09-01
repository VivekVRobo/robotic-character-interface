#pragma once

#include <stddef.h>
#include <stdint.h>

namespace rci {
constexpr uint8_t kProtocolVersion = 1;

namespace protocol {
constexpr uint8_t kMagic0 = 0x52;
constexpr uint8_t kMagic1 = 0x43;
constexpr size_t kHeaderSize = 8;
constexpr size_t kCrcSize = 2;
constexpr size_t kFrameOverhead = kHeaderSize + kCrcSize;
constexpr uint16_t kMaxPayloadSize = 512;
constexpr size_t kNrf24MaxFrameSize = 32;
constexpr size_t kGloveTelemetryPayloadSize = 21;
constexpr size_t kGloveTelemetryFrameSize = kFrameOverhead + kGloveTelemetryPayloadSize;
constexpr size_t kAcknowledgementPayloadSize = 3;
constexpr uint8_t kMaxRobotTelemetryJoints = 8;
constexpr size_t kRobotTelemetryHeadSize = 9;
constexpr size_t kRobotJointTelemetrySize = 7;

static_assert(kGloveTelemetryFrameSize <= kNrf24MaxFrameSize,
              "Glove telemetry frame must fit one nRF24 payload");

enum class MessageType : uint8_t {
  kGloveTelemetry = 0x01,
  kHeartbeat = 0x02,
  kValidatedMotionCommand = 0x03,
  kEstop = 0x04,
  kAck = 0x05,
  kNack = 0x06,
  kRobotTelemetry = 0x07,
};

enum class AckStatus : uint8_t {
  kOk = 0x00,
  kRejected = 0x01,
  kStale = 0x02,
  kInvalid = 0x03,
};

struct GloveTelemetry {
  uint16_t device_time_ms_mod;
  int16_t accel_x_mg;
  int16_t accel_y_mg;
  int16_t accel_z_mg;
  int16_t gyro_x_cdeg_s;
  int16_t gyro_y_cdeg_s;
  int16_t gyro_z_cdeg_s;
  int16_t pitch_cdeg;
  int16_t roll_cdeg;
  uint16_t battery_mv;
  uint8_t flags;
};

struct RobotJointTelemetry {
  uint8_t joint_id;
  int16_t position_cdeg;
  int16_t velocity_cdeg_s;
  uint16_t current_ma;
};

struct RobotTelemetry {
  uint32_t uptime_ms;
  uint8_t state;
  uint8_t flags;
  uint16_t supply_mv;
  uint8_t joint_count;
  RobotJointTelemetry joints[kMaxRobotTelemetryJoints];
};

inline void WriteU16Le(uint8_t* out, uint16_t value) {
  out[0] = static_cast<uint8_t>(value & 0xFFu);
  out[1] = static_cast<uint8_t>((value >> 8) & 0xFFu);
}

inline void WriteI16Le(uint8_t* out, int16_t value) {
  WriteU16Le(out, static_cast<uint16_t>(value));
}

inline void WriteU32Le(uint8_t* out, uint32_t value) {
  out[0] = static_cast<uint8_t>(value & 0xFFu);
  out[1] = static_cast<uint8_t>((value >> 8) & 0xFFu);
  out[2] = static_cast<uint8_t>((value >> 16) & 0xFFu);
  out[3] = static_cast<uint8_t>((value >> 24) & 0xFFu);
}

inline uint16_t Crc16CcittFalse(const uint8_t* data, size_t length) {
  uint16_t crc = 0xFFFFu;
  for (size_t i = 0; i < length; ++i) {
    crc ^= static_cast<uint16_t>(data[i]) << 8;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      if ((crc & 0x8000u) != 0u) {
        crc = static_cast<uint16_t>((crc << 1) ^ 0x1021u);
      } else {
        crc = static_cast<uint16_t>(crc << 1);
      }
    }
  }
  return crc;
}

inline size_t EncodeAcknowledgementPayload(uint16_t acknowledged_sequence,
                                           AckStatus status,
                                           uint8_t* out,
                                           size_t capacity) {
  if (out == nullptr || capacity < kAcknowledgementPayloadSize) {
    return 0;
  }
  WriteU16Le(out, acknowledged_sequence);
  out[2] = static_cast<uint8_t>(status);
  return kAcknowledgementPayloadSize;
}

inline size_t EncodeGloveTelemetryPayload(const GloveTelemetry& telemetry,
                                          uint8_t* out,
                                          size_t capacity) {
  if (out == nullptr || capacity < kGloveTelemetryPayloadSize) {
    return 0;
  }
  size_t offset = 0;
  WriteU16Le(out + offset, telemetry.device_time_ms_mod);
  offset += 2;
  WriteI16Le(out + offset, telemetry.accel_x_mg);
  offset += 2;
  WriteI16Le(out + offset, telemetry.accel_y_mg);
  offset += 2;
  WriteI16Le(out + offset, telemetry.accel_z_mg);
  offset += 2;
  WriteI16Le(out + offset, telemetry.gyro_x_cdeg_s);
  offset += 2;
  WriteI16Le(out + offset, telemetry.gyro_y_cdeg_s);
  offset += 2;
  WriteI16Le(out + offset, telemetry.gyro_z_cdeg_s);
  offset += 2;
  WriteI16Le(out + offset, telemetry.pitch_cdeg);
  offset += 2;
  WriteI16Le(out + offset, telemetry.roll_cdeg);
  offset += 2;
  WriteU16Le(out + offset, telemetry.battery_mv);
  offset += 2;
  out[offset++] = telemetry.flags;
  return offset;
}

inline size_t EncodeRobotTelemetryPayload(const RobotTelemetry& telemetry,
                                          uint8_t* out,
                                          size_t capacity) {
  if (telemetry.joint_count == 0u || telemetry.joint_count > kMaxRobotTelemetryJoints) {
    return 0;
  }
  const size_t required =
      kRobotTelemetryHeadSize + telemetry.joint_count * kRobotJointTelemetrySize;
  if (out == nullptr || capacity < required) {
    return 0;
  }

  size_t offset = 0;
  WriteU32Le(out + offset, telemetry.uptime_ms);
  offset += 4;
  out[offset++] = telemetry.state;
  out[offset++] = telemetry.flags;
  WriteU16Le(out + offset, telemetry.supply_mv);
  offset += 2;
  out[offset++] = telemetry.joint_count;
  for (uint8_t index = 0; index < telemetry.joint_count; ++index) {
    const RobotJointTelemetry& joint = telemetry.joints[index];
    if (joint.joint_id == 0u) {
      return 0;
    }
    out[offset++] = joint.joint_id;
    WriteI16Le(out + offset, joint.position_cdeg);
    offset += 2;
    WriteI16Le(out + offset, joint.velocity_cdeg_s);
    offset += 2;
    WriteU16Le(out + offset, joint.current_ma);
    offset += 2;
  }
  return offset;
}

inline size_t BuildFrame(MessageType type,
                         uint16_t sequence,
                         const uint8_t* payload,
                         uint16_t payload_length,
                         uint8_t* out,
                         size_t capacity) {
  const size_t frame_size = kFrameOverhead + payload_length;
  if (out == nullptr || payload_length > kMaxPayloadSize || capacity < frame_size ||
      (payload_length > 0 && payload == nullptr)) {
    return 0;
  }

  out[0] = kMagic0;
  out[1] = kMagic1;
  out[2] = kProtocolVersion;
  out[3] = static_cast<uint8_t>(type);
  WriteU16Le(out + 4, sequence);
  WriteU16Le(out + 6, payload_length);
  for (uint16_t i = 0; i < payload_length; ++i) {
    out[kHeaderSize + i] = payload[i];
  }
  const uint16_t crc = Crc16CcittFalse(out, kHeaderSize + payload_length);
  WriteU16Le(out + kHeaderSize + payload_length, crc);
  return frame_size;
}

}  // namespace protocol
}  // namespace rci
