# Master Architecture

This document is the architectural source of truth for the Robotic Character Interface.

## Mission

Translate human gesture, voice, and text into character-specific speech and physical expression while guaranteeing that AI/personality components cannot directly command actuators.

## Canonical control path

```text
Human Input
  -> Input Adapters
  -> Structured Perception
  -> Cognition / Character
  -> Structured CharacterResponse
  -> Behavior Planner
  -> Motion Request
  -> Trajectory Planner
  -> Motion Safety Supervisor
  -> ValidatedMotionCommand
  -> Robot Gateway
  -> Robot MCU
  -> Firmware Safety
  -> Servo Driver
  -> Physical Robot
```

## System invariants

1. No AI/character/gesture/API/frontend module directly controls PWM or servos.
2. Every physical movement passes deterministic motion safety.
3. Invalid, expired, duplicated, replayed, or stale motion commands cannot execute.
4. Communication loss transitions to a defined safe state.
5. Hardware E-stop remains independent from the host software path.
6. Character profiles may reduce motion speed/amplitude but may never raise hard safety maxima.
7. Every physical action is traceable by command/interaction identifiers and audit events.
8. Simulation/replay share interfaces with real hardware.
9. Hardware claims are marked unverified until measured.
10. Critical subsystem failure cannot silently create unrestricted motion.

## Runtime states

`BOOT -> SELF_TEST -> CALIBRATING -> IDLE -> ARMED -> EXECUTING`

Exceptional states: `DEGRADED`, `FAULT`, `ESTOP`, `SHUTDOWN`.

Motion is allowed only in explicitly configured states.

## Core backend boundaries

- `core/`: lifecycle/orchestration only
- `events/`: typed pub/sub
- `state/`: authoritative state snapshots/transitions
- `health/`: component health aggregation
- `protocols/`: host/firmware packet contracts
- `hardware/`: serial/radio adapters and gateways
- `gesture/`: calibration/filtering/features/classification
- `cognition/`: intent, MeaningFrame, context, structured generation
- `characters/`: canon, emotion, profiles, validation
- `behavior/`: semantic behavior plans/motion primitives
- `robotics/`: robot model, FK/IK, trajectories
- `safety/`: hard deterministic physical constraints
- `telemetry/`: metrics, recording, replay
- `audit/`: append-only/hash-chain critical events
- `simulation/`: fake hardware/scenario/fault injection
- `interfaces/`: CLI/API/WebSocket only

## Hardware boundary

The glove reports human motion telemetry, not servo angles. The robot MCU accepts only validated robot commands from the host and applies independent firmware validation, watchdog, E-stop, and joint constraints.

## Physical verification boundary

Software can be simulation-validated without hardware. Production-ready status additionally requires measured joint limits, robot geometry, power/current budget, physical E-stop test, watchdog loss test, radio metrics, gesture dataset/accuracy, motion latency, repeatability, positional error, and soak evidence.
