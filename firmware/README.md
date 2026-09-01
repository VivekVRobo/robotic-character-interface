# Firmware

- `shared/`: protocol/checksum/watchdog primitives
- `glove/`: MPU6050 gesture telemetry transmitter; never sends servo targets
- `gateway/`: radio telemetry bridge
- `robot/`: validated host commands -> MCU safety -> PCA9685
