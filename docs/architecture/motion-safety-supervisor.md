# MotionSafetySupervisor

PR-011 establishes `MotionSafetySupervisor` as the authoritative application-layer composition point for motion safety.

## Ordering

The supervisor evaluates motion in this order:

1. Synchronize the physical E-stop observation into the sticky lifecycle.
2. Feed the current heartbeat age into the watchdog lifecycle.
3. Apply lifecycle precedence.
   - latched/physical E-stop -> `ESTOP`
   - watchdog disarmed -> `REJECT`
   - watchdog unhealthy -> `REJECT`
4. Run PR-009 dynamic eligibility, which itself runs PR-008 static eligibility first.
5. Only if every layer approves, mint an immutable `MotionAuthorization`.

```text
MotionCandidate + MotionDynamics
          ↓
MotionSafetySupervisor
          ├─ PR-010 lifecycle / E-stop / watchdog
          └─ PR-009 dynamic eligibility
                    └─ PR-008 static eligibility
          ↓
APPROVE / REJECT / ESTOP
          ↓ APPROVE only
MotionAuthorization
          ↓ future RobotGateway
ValidatedMotionCommand
          ↓ MCU
```

## Authorization boundary

`MotionAuthorization` is not a protocol message and is not actuator output. It contains:

- a unique authorization ID
- the lifecycle sequence that approved it
- immutable joint targets
- the already-validated Cartesian point
- the configured command TTL
- configured velocity and acceleration maxima

It contains no PWM values or servo-driver instructions.

A mandatory safety test scans `src/rci` and fails if another application module attempts to construct `MotionAuthorization` directly. This makes supervisor-only authorization minting a CI-enforced architecture rule rather than documentation alone.

## Hardware status

PR-011 does not change any robot or servo measurements. The canonical repository configuration remains hardware-unverified, so the real configuration still cannot produce a motion authorization. Tests that exercise successful authorization use explicitly synthetic verified fixtures only.

## Next boundary

RobotGateway will later accept `MotionAuthorization` and translate it into the existing `ValidatedMotionCommand` protocol payload. Hardware and firmware remain responsible for their own independent safety checks.
