# V005 Integrated Adversarial Fault Campaign

V005 is the final software-only validation gate before any single-servo hardware-in-the-loop work.

The campaign attacks the same cross-repository path proven by V004:

```text
AureliaCognitiveRuntime
  -> rci.character_response.v1
  -> RCI CharacterResponse validation
  -> BehaviorPlanner
  -> test-only deterministic simulation pose
  -> MotionSafetySupervisor
  -> MotionAuthorization
  -> RobotGateway
  -> SimulatedProtocolLink
  -> compiled C++ RobotRuntime
  -> ACK / NACK
```

The production RobotModel/Motion Planner is still not implemented. The synthetic pose and verified envelope used by these tests exist only in the software-validation test process and are not hardware calibration evidence.

## Required adversarial cases

| Fault | Expected software response | Recovery evidence |
| --- | --- | --- |
| unverified Aurelia response | RCI contract rejects before behavior planning | use a newly verified response |
| malformed Aurelia response | RCI contract rejects before behavior planning | use a schema-valid response |
| actuator-field injection | strict character contract rejects extra servo/PWM content | semantic-only response accepted |
| stale command age | MotionSafetySupervisor rejects, no authorization | fresh candidate may be evaluated |
| stale heartbeat | watchdog lifecycle latches E-stop | fresh heartbeat alone is insufficient; explicit manual reset required |
| firmware command before heartbeat | firmware NACK `REJECTED` | heartbeat then retry may proceed |
| E-stop after host authorization | firmware latches E-stop and NACKs the previously authorized motion | no implicit recovery |
| duplicate/out-of-order wire sequence | firmware NACK `STALE` | only a fresh sequence can proceed |
| duplicate accepted motion command UUID on a fresh sequence | firmware NACK `STALE` | a genuinely new authorization is required |
| ACK timeout | RobotGateway fails closed | queued request is drained and a later request can succeed |
| ACK sequence mismatch | RobotGateway protocol error | mismatched acknowledgement is never accepted |
| corrupted ACK frame | checksum fault is surfaced | later valid frame can recover cleanly |
| transport disconnect | normalized RobotGateway send failure | establish a new transport/gateway session |

## Replay policy

Firmware uses two independent replay checks:

1. **wire sequence freshness**: modulo-16-bit sequence numbers must advance within the forward half-range, so duplicates and out-of-order frames are rejected while `65535 -> 0` wrap remains valid;
2. **motion command identity**: once a structurally valid motion command reaches the safe deferred state, the 128-bit command UUID is remembered and the same command UUID is rejected even if resent under a new wire sequence.

Commands rejected because firmware is not yet safe are not remembered as executed/deferred commands, allowing a legitimate retry after the required safety precondition is restored.

## Interpretation of a green V005 gate

A green V005 gate means the current software stack has demonstrated fail-closed behavior and deterministic recovery for the listed software faults using simulation and the compiled firmware runtime.

It does **not** prove:

- physical servo calibration;
- measured robot geometry or workspace;
- electrical power integrity;
- real E-stop wiring;
- real watchdog timing under MCU load;
- physical collision safety;
- actuator accuracy, repeatability, torque, thermal behavior, or mechanical limits.

Those claims remain blocked until the later physical HIL and measurement milestones.
