# RobotGateway Authorization Boundary

`RobotGateway` is the only host-side application boundary allowed to translate a `MotionAuthorization` into protocol message type `VALIDATED_MOTION_COMMAND`.

## Required path

```text
MotionCandidate
  -> MotionSafetySupervisor
  -> MotionAuthorization
  -> RobotGateway
  -> ValidatedMotionCommand
  -> ProtocolTransport
  -> robot firmware
  -> ACK/NACK
```

No character, cognition, gesture, API, behavior, motion-planning, or generic hardware module may construct the validated-motion wire command directly.

## Joint identity

Servo `channel` and protocol `protocol_id` are intentionally separate. The channel is an actuator-driver mapping. The protocol ID is a stable software identifier used on the host/MCU wire contract. PR-013 assigns protocol IDs without changing or claiming any physical measurements.

## No hidden quantization

A `MotionAuthorization` has already passed safety checks. `RobotGateway` therefore refuses to round authorized angles or rate limits while converting degrees to centidegrees. Values must be exactly representable in protocol units or the request is rejected before transmission.

## Explicit acceptance

A successful byte write is not proof of robot acceptance. Every host request handled by `RobotGateway` requires an ACK/NACK payload whose acknowledged sequence matches the outstanding frame. Timeouts, unexpected message types, malformed acknowledgements, sequence mismatches, NACK, or non-OK status all fail closed.

## Firmware behavior in PR-013

The robot firmware validates frame integrity and the structural shape of `ValidatedMotionCommand`. It ACKs a valid command only when its independent heartbeat/watchdog state is ready. Even then, motion execution remains deferred: PR-013 adds no servo driver, PWM output, or physical actuator authorization.
