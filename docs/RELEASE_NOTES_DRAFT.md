# Draft Release Notes — v0.1.0

## v0.1.0 — Safety-Governed Robotic Character Interface (Simulation Release)

This is the first software-reference release of the Robotic Character Interface: a multimodal character-embodiment robotics platform where character/AI intent is separated from deterministic planning, motion authorization, transport, firmware and telemetry boundaries.

### Release statement

**Software-complete and simulation-validated. Physical hardware validation pending.**

### What this release demonstrates

- text/simulated voice/gesture input into a structured meaning and character-response path;
- verified `rci.character_response.v1` integration boundary;
- deterministic `BehaviorPlanner` and simulation embodiment planning;
- robot trajectory generation behind `MotionSafetySupervisor` and `MotionAuthorization`;
- `RobotGateway` protocol boundary and compiled C++ firmware safety runtime;
- engineering-predicted digital twin with simulation-only telemetry;
- FastAPI/WebSocket runtime and React/TypeScript dashboard;
- deterministic simulation benchmark evidence;
- production-model motion-safety challenge evidence for approval plus state, E-stop, joint/workspace, freshness, velocity and acceleration rejection paths;
- cross-repository Aurelia → RCI → firmware/digital-twin software E2E validation.

### CI release gate

The exact tag commit must have all four workflows green:

1. Backend CI
2. Safety and Contract CI
3. Frontend CI
4. Cross-Repo Software E2E

### Evidence boundary

The simulation benchmark and motion-safety evidence are explicitly software/simulation evidence. They do not prove physical actuator safety, a certified safety system, or hardware performance.

No claim is made for measured PWM calibration, real current/voltage behavior, physical E-stop wiring, workspace/collision validation, endpoint accuracy, repeatability, thermal behavior or physical latency.

### Physical next step

The HIL/physical maturity track requires measured joint geometry and calibration, actuator/power wiring, physical E-stop proof, real telemetry, repeatability/accuracy tests, failure cases and real media.

### Release gate

Before publishing the GitHub Release, complete `docs/RELEASE_CHECKLIST.md` and keep `docs/SOFTWARE_RELEASE.md` aligned with the exact tagged architecture.

This release must not be described as safety-certified or production-ready.
