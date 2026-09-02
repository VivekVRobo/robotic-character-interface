# Robotic Character Interface

A safety-governed multimodal AI character embodiment robotics platform that translates human input and verified character semantics into deterministic robot behavior through explicit planning, safety, transport, firmware, and telemetry boundaries.

## Status

**v0.1.0 — Software-complete and simulation-validated. Physical hardware validation pending.**

The repository is runnable end-to-end against an engineering-predicted 4-DOF digital twin. Predicted hardware values are explicitly marked `simulation_only: true`, `hardware_verified: false`, and `provenance.source: engineering_prediction`; they are not presented as measured hardware evidence.

## Software path

```text
Text / simulated voice / MPU6050 motion gesture
        ↓
MeaningFrame / multimodal correlation
        ↓
Aurelia character intelligence
        ↓
verified rci.character_response.v1
        ↓
BehaviorPlanner
        ↓
simulation embodiment profile
        ↓
RobotController + trajectory
        ↓
MotionSafetySupervisor
        ↓
MotionAuthorization
        ↓
RobotGateway
        ↓
protocol-v1 command
        ↓
DigitalTwinProtocolDevice
        ↓
DigitalTwinRobot
        ↓
telemetry / FastAPI / WebSocket / React dashboard
```

The repository separately compiles and tests the C++ robot firmware safety runtime. Physical actuation remains disabled until real HIL evidence exists.

## Core invariant

No AI, character, gesture, API, or frontend component may directly control actuators. Any future physical motion must pass through deterministic planning, `MotionSafetySupervisor`, `RobotGateway`, MCU validation, and the hardware driver boundary.

## Validation

A release requires all four GitHub Actions gates green on the same commit:

- **Backend CI** — Ruff, formatting, strict mypy, unit tests, deterministic digital-twin soak benchmark.
- **Safety and Contract CI** — safety regressions, protocol vectors, compiled C++ robot runtime and HIL guard.
- **Frontend CI** — TypeScript typecheck, React/Vitest tests, production build.
- **Cross-Repo Software E2E** — real Aurelia + RCI integration, compiled firmware validation, adversarial faults, and final digital-twin execution.

Backend CI uploads the deterministic `rci-simulation-benchmark` artifact. See `docs/SOFTWARE_RELEASE.md` and `reports/simulation/README.md`.

## Run the simulation service

```bash
python -m pip install -e '.[dev]'
rci
```

Aurelia is expected at `http://127.0.0.1:5000` by default. Override with `AURELIA_URL` if needed.

For the dashboard:

```bash
cd dashboard
npm install
npm run dev
```

The live dashboard consumes the FastAPI snapshot/interaction endpoints and WebSocket telemetry stream and labels digital-twin data as simulation-only.

## Repository map

- `src/rci/` — runtime, cognition boundary, behavior, robotics, safety, transport, API and simulation
- `dashboard/` — React + TypeScript live operator/diagnostic UI
- `firmware/` — glove, gateway and robot MCU safety/runtime code
- `characters/` — character integration assets and contracts
- `configs/` — production-unverified config plus simulation reference profiles
- `schemas/` — protocol and data contracts
- `tests/` — unit, integration, safety, fault, HIL and cross-repo E2E tests
- `tools/` — reproducible software validation/benchmark utilities
- `reports/` — simulation evidence guidance and CI-generated artifacts
- `hardware/` — future physical BOM/wiring/calibration evidence
- `docs/` — architecture, roadmap, HIL and release documentation

## Physical validation still pending

No claim is made yet for real servo movement, measured PWM calibration, measured current/voltage, real workspace/collision limits, physical E-stop wiring, mechanical repeatability, or real robot photographs/video/telemetry. The existing HIL readiness framework is designed to accept those measurements later without changing the software architecture.
