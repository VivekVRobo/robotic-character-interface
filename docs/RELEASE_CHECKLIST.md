# RCI v0.1.0 Release Checklist

This checklist operationalizes [`SOFTWARE_RELEASE.md`](SOFTWARE_RELEASE.md). A tag is acceptable only when the exact tagged commit satisfies every software gate below. Physical-hardware validation remains a separate maturity track.

## Exact-commit CI gate

- [ ] Backend CI is green.
- [ ] Safety and Contract CI is green.
- [ ] Frontend CI is green.
- [ ] Cross-Repo Software E2E is green against the intended Aurelia revision.
- [ ] All four workflows correspond to the exact commit selected for the tag.

## Machine-readable evidence

- [ ] `rci-simulation-benchmark` is generated successfully by Backend CI.
- [ ] Deterministic digital-twin benchmark reports `simulation_only: true` and does not claim physical measurement.
- [ ] `rci-motion-safety-evidence` is generated successfully by Safety and Contract CI.
- [ ] The production-model safety campaign covers baseline authorization plus state, E-stop, joint, workspace, freshness, velocity, and acceleration rejection cases.
- [ ] Safety evidence remains explicitly `simulation_only: true`, `hardware_verified: false`, and `physical_motion: false`.
- [ ] Cross-repository tests validate the real `rci.character_response.v1` boundary rather than a copied fixture alone.

## Safety architecture gate

- [ ] No AI, character, gesture, API, or frontend path can mint actuator commands directly.
- [ ] Motion requires `BehaviorPlanner` → embodiment planner → `RobotController` → `MotionSafetySupervisor` → `MotionAuthorization` → `RobotGateway`.
- [ ] E-stop/watchdog paths fail closed in software tests.
- [ ] Replay/sequence protection and firmware ACK/NACK behavior remain tested.
- [ ] The physical firmware path still contains no silently enabled actuator driver.

## Documentation and claim boundary

- [ ] README status remains `Software-complete and simulation-validated. Physical hardware validation pending.` unless stronger evidence exists.
- [ ] `docs/SOFTWARE_RELEASE.md` matches the tagged architecture.
- [ ] `docs/validation/V005_FAULT_CAMPAIGN.md` and `V006_MOTION_SAFETY_EVIDENCE.md` match the current tests/tools.
- [ ] Predicted reference-arm values remain labeled `simulation_only`, `hardware_verified: false`, with engineering-prediction provenance.
- [ ] No measured current, PWM calibration, workspace, E-stop wiring, accuracy, repeatability, thermal, or physical-latency claim appears without real hardware evidence.

## Packaging/release notes

- [ ] Python package installs from the tagged tree with `pip install -e '.[dev]'` for development validation.
- [ ] Dashboard dependency install/typecheck/tests/build remain documented and reproducible.
- [ ] Release notes link the simulation benchmark and motion-safety evidence artifacts/workflows.
- [ ] Release notes list known physical-validation gaps.
- [ ] Release notes do not call the project safety-certified or production-ready.

## Recommended release title

`v0.1.0 — Safety-Governed Robotic Character Interface (Simulation Release)`

## Recruiter review path

1. `README.md` — system boundary and maturity statement;
2. `docs/SOFTWARE_RELEASE.md` — release scope;
3. `docs/validation/V006_MOTION_SAFETY_EVIDENCE.md` — deterministic production-model safety campaign;
4. `tools/run_motion_safety_evidence.py` — machine-readable evidence generator;
5. `src/rci/safety/` + `src/rci/hardware/robot_gateway.py` — authority boundary;
6. cross-repo E2E workflow/tests — Aurelia→RCI→firmware/digital-twin proof;
7. this checklist — exact tag gate.
