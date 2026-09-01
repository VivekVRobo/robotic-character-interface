#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../../firmware/robot/runtime.h"

namespace {

int HexValue(char ch) {
  if (ch >= '0' && ch <= '9') {
    return ch - '0';
  }
  if (ch >= 'a' && ch <= 'f') {
    return 10 + (ch - 'a');
  }
  if (ch >= 'A' && ch <= 'F') {
    return 10 + (ch - 'A');
  }
  return -1;
}

bool DecodeHex(const std::string& hex, std::vector<uint8_t>* output) {
  if (output == nullptr || hex.size() % 2u != 0u) {
    return false;
  }
  output->clear();
  output->reserve(hex.size() / 2u);
  for (size_t index = 0; index < hex.size(); index += 2u) {
    const int high = HexValue(hex[index]);
    const int low = HexValue(hex[index + 1u]);
    if (high < 0 || low < 0) {
      return false;
    }
    output->push_back(static_cast<uint8_t>((high << 4) | low));
  }
  return true;
}

}  // namespace

int main() {
  rci::robot::RobotRuntime runtime;
  std::string line;

  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    uint32_t now_ms = 0u;
    std::string frame_hex;
    if (!(input >> now_ms >> frame_hex)) {
      std::cout << "-1 3" << std::endl;
      continue;
    }

    std::vector<uint8_t> frame;
    if (!DecodeHex(frame_hex, &frame)) {
      std::cout << "-1 3" << std::endl;
      continue;
    }

    const auto dispatch = runtime.HandleFrame(frame.data(), frame.size(), now_ms);
    const auto ack_status = rci::robot::AckStatusForDispatch(dispatch);
    std::cout << static_cast<int>(dispatch) << ' ' << static_cast<int>(ack_status)
              << std::endl;
  }

  return 0;
}
