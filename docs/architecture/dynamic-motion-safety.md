# Dynamic Motion Safety

PR-009 extends PR-008 with deterministic command freshness and dynamic-rate checks. Static joint/workspace eligibility remains the first gate and must approve before dynamic checks run.

## Evaluation order

```text
MotionCandidate
  -> PR-008 static eligibility
  -> command age / TTL
  -> heartbeat age / timeout
  -> required velocity samples
  -> required acceleration samples
  -> velocity limit
  -> acceleration limit
  -> APPROVE / REJECT / ESTOP
```

A PR-009 `APPROVE` still does not authorize actuators. It only means the candidate may advance to later watchdog, trajectory, collision, kinematic, and supervisor checks.

## Canonical policy

Dynamic thresholds are derived from the existing `configs/safety.yaml` rather than duplicated in code:

- command TTL: 250 ms
- heartbeat timeout: 500 ms
- maximum velocity: 60 deg/s
- maximum acceleration: 180 deg/s^2

These are software safety-policy limits already present in the repository. They are not claims about measured hardware capability.

## Fail-closed rules

- command and heartbeat ages must be finite and non-negative;
- equality with TTL/timeout remains valid, values above are stale;
- every target joint requires a velocity and acceleration sample;
- non-finite dynamic samples are rejected;
- absolute velocity and acceleration are compared to configured maxima;
- dynamic samples referencing unknown joints are rejected;
- rate violations are rejected, not silently clamped.

## Deferred layers

PR-010 adds E-stop/watchdog lifecycle behavior. PR-011 composes these checks into the authoritative `MotionSafetySupervisor`.
