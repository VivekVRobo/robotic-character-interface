# Reference Digital Twin

The repository can be fully exercised without physical hardware by using `configs/simulation/reference_arm.yaml`.

## Evidence status

The reference profile is an **engineering prediction**, not a measurement. It is permanently marked:

- `simulation_only: true`
- `hardware_verified: false`
- provenance source `engineering_prediction`

These values must never be copied into the production `configs/robot.yaml` or `configs/servos.yaml` as verified physical values.

## Reference assumptions

The current digital twin represents a generic four-DOF hobby arm:

- base height: 80 mm
- shoulder link: 120 mm
- forearm link: 120 mm
- tool extension: 55 mm
- base, shoulder, elbow and gripper joints
- conservative software velocity/acceleration limits defined per joint

These are intentionally plausible rather than manufacturer-specific. Their purpose is to make kinematics, planning, control, simulation, fault testing and UI telemetry reproducible now.

## Replacement rule

When real hardware exists, measured geometry and limits replace the reference profile through a separate hardware-calibration path. No architecture change should be required.

```text
reference prediction -> digital twin -> software validation

later:

measured geometry -> physical profile -> HIL validation
```

## Robotics core

`rci.robotics` now provides:

1. strict reference-profile loading;
2. deterministic `RobotModel` joint validation;
3. forward kinematics;
4. inverse kinematics with joint-limit filtering and seed-based branch selection;
5. sampled workspace estimation;
6. bounded cubic trajectory generation;
7. a Cartesian `RobotController` that emits the existing `MotionCandidate` and `MotionDynamics` safety contracts.

The controller does **not** mint `MotionAuthorization` and does not talk to firmware. The existing `MotionSafetySupervisor -> RobotGateway` boundary remains authoritative.
