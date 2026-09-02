# RCI v0.1.0 Software Release

## Release statement

**Software-complete and simulation-validated. Physical hardware validation pending.**

This statement applies to the v0.1.0 software architecture and reference digital twin. It does not claim that a physical robot, servo bank, wiring harness, power system, mechanical envelope, or emergency-stop circuit has been measured or validated.

## Proven software path

```text
Text / simulated voice / MPU6050 motion gesture
        ↓
MultimodalCorrelator → MeaningFrame
        ↓
Aurelia hardened cognitive endpoint
        ↓
verified rci.character_response.v1
        ↓
BehaviorPlanner
        ↓
SimulationBehaviorEmbodimentPlanner
        ↓
RobotController / trajectory generation
        ↓
MotionSafetySupervisor
        ↓
MotionAuthorization
        ↓
RobotGateway
        ↓
protocol-v1 ValidatedMotionCommand
        ↓
SimulatedProtocolLink
        ↓
DigitalTwinProtocolDevice
        ↓
DigitalTwinRobot
        ↓
protocol robot telemetry / WebSocket dashboard
```

The same repository also compiles and validates the C++ robot firmware safety runtime. The physical firmware intentionally contains no enabled actuator driver in this release.

## Validation gates

The release is gated by four GitHub Actions workflows:

1. **Backend CI** — Ruff, formatting, strict mypy, unit tests, and deterministic digital-twin soak benchmark.
2. **Safety and Contract CI** — safety regressions plus Python/C++ protocol and firmware runtime validation.
3. **Frontend CI** — TypeScript typecheck, React/Vitest behavior tests, and production build.
4. **Cross-Repo Software E2E** — checks out Aurelia and RCI together and validates the real character contract, compiled firmware path, adversarial fault campaign, and final Aurelia→digital-twin runtime.

A release is acceptable only when all four workflows are green on the same exact commit.

## Simulation evidence

Backend CI runs:

```bash
python tools/run_simulation_benchmark.py \
  --repetitions 3 \
  --output reports/simulation/ci-benchmark.json
```

The workflow uploads `rci-simulation-benchmark` as a CI artifact. The report contains only deterministic software metrics: behavior cycles, simulated motion steps/duration, simulated current, E-stop recoveries, gateway ACK/reject counts, final telemetry, and a SHA-256 digest.

No field in the benchmark is physical measurement evidence.

## Run locally

Requirements:

- Python 3.12+
- Node.js for the dashboard
- a local checkout of this repository
- Aurelia running separately at `http://127.0.0.1:5000` by default

Install and launch RCI:

```bash
python -m pip install -e '.[dev]'
rci
```

Optional environment variables:

```text
AURELIA_URL=http://127.0.0.1:5000
RCI_HOST=127.0.0.1
RCI_PORT=8000
RCI_REFERENCE_PROFILE=configs/simulation/reference_arm.yaml
```

Dashboard development server:

```bash
cd dashboard
npm install
npm run dev
```

The dashboard consumes `/api/dashboard/snapshot`, `/api/simulation/interact`, and `/ws/telemetry`. It labels all robot telemetry as simulation-only and not measured hardware.

## Hardware prediction policy

`configs/simulation/reference_arm.yaml` is an engineering reference profile. It is deliberately marked:

```yaml
simulation_only: true
hardware_verified: false
provenance:
  source: engineering_prediction
```

Predicted geometry, joint limits, speeds, accelerations, supply voltage, current, and behavior poses are allowed only in the simulation/digital-twin path. They must never populate production hardware-verification fields.

## What remains physical

The following remain pending until real hardware exists:

- measured joint min/max/neutral values
- measured pulse-width/PWM calibration
- measured supply voltage/current behavior
- verified actuator/logic rail wiring
- physical E-stop wiring and power-cut proof
- real workspace and collision testing
- mechanical hard-stop validation
- real latency, repeatability, accuracy, thermal and soak evidence
- real photographs/video/telemetry

The HIL readiness framework is already implemented so these measurements can replace predicted values later without redesigning the software architecture.
