# Deterministic Motion Safety Models

PR-008 establishes the first deterministic eligibility boundary for physical robot motion. It does not authorize actuator commands and it does not perform trajectory, velocity, acceleration, freshness, collision, or kinematic checks. Those remain later safety layers.

## Safety invariant

Physical motion is fail-closed. Numeric configuration values are never treated as measured truth unless their corresponding hardware verification flag is true and the complete constraint set is internally valid.

The canonical repository intentionally keeps physical measurements unset:

- `configs/servos.yaml` has `hardware_verified: false` and null joint angles.
- `configs/robot.yaml` has `hardware_verified: false` and null workspace bounds.

Therefore the canonical development configuration is not eligible for physical movement.

## Eligibility pipeline

```text
MotionCandidate
  -> E-stop priority check
  -> allowed runtime-state check
  -> verified joint-envelope check
  -> known finite joint-target check
  -> verified workspace-envelope check
  -> finite workspace-target check
  -> MotionEligibility: APPROVE / REJECT / ESTOP
```

`APPROVE` means only that the candidate may advance to later deterministic safety checks. It is not equivalent to actuator authorization.

## Verification semantics

A joint constraint is authoritative only when:

1. servo hardware verification is true,
2. min/neutral/max values are all present,
3. `min < neutral < max`.

A workspace is authoritative only when:

1. robot hardware verification is true,
2. all X/Y/Z min/max bounds are present,
3. every axis satisfies `min < max`.

Adding placeholder numbers while leaving `hardware_verified: false` cannot make motion eligible.

## Workspace target requirement

PR-008 requires a Cartesian workspace point alongside joint targets for physical eligibility. This is deliberately conservative because joint limits alone cannot prove that the arm remains inside its measured physical workspace.

Future robot-model and FK work will derive workspace positions from trajectories instead of trusting callers to provide them.

## Deferred checks

PR-009 will add velocity, acceleration, command-freshness, and heartbeat checks. Later milestones add robot kinematics, trajectory validation, collision checks, watchdogs, and the complete `MotionSafetySupervisor`.
