# Repository Implementation Plan

## Monorepo ownership

`src/rci/` contains application code. Hardware-facing libraries are isolated under `hardware/`; business logic never imports serial/PCA9685/nRF24 implementation details directly.

## Python package map

```text
src/rci/
  app.py
  bootstrap.py
  version.py
  core/
  domain/
  config/
  events/
  state/
  health/
  protocols/
  hardware/
  gesture/
  cognition/
  characters/
  voice/
  behavior/
  robotics/
  safety/
  telemetry/
  audit/
  simulation/
  experiments/
  interfaces/
```

## Frontend map

`dashboard/src/` will contain `api`, `websocket`, `store`, `hooks`, `components`, `pages`, `types`, and `utils`. The dashboard consumes API/WebSocket contracts; it never reaches hardware directly.

## Firmware map

- `firmware/shared/`: protocol/checksum/timing/watchdog primitives
- `firmware/glove/`: IMU calibration/orientation/radio telemetry
- `firmware/gateway/`: nRF24 -> validated serial bridge
- `firmware/robot/`: command validation, E-stop, heartbeat, trajectory execution, PCA9685 output, telemetry

## Test map

- `unit`: algorithm/component tests
- `contract`: schema and Python/firmware protocol compatibility
- `integration`: subsystem pipelines
- `simulation`: fake hardware and replay
- `safety`: mandatory negative/boundary tests
- `fault_injection`: disconnect/corruption/crash/replay tests
- `hil`: explicit physical hardware tests
- `e2e`: complete user interaction flows

## Definition of done

A major module requires implementation, configuration, tests, error handling, health/telemetry where relevant, and documentation. Safety-critical modules additionally require negative, boundary, and fault tests.
