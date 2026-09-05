# Cross-Repository Software E2E Validation

V004 proves the software path between the stabilized Aurelia cognitive runtime and the RCI robot-firmware boundary without claiming physical hardware validation.

## Executed path

```text
Real AureliaCognitiveRuntime cycle
  -> serialize_cognitive_cycle
  -> exact rci.character_response.v1 payload
  -> RCI parse_character_response
  -> BehaviorPlanner
  -> test-only deterministic simulation pose profile
  -> MotionSafetySupervisor
  -> MotionAuthorization
  -> RobotGateway
  -> ProtocolTransport
  -> SimulatedProtocolLink
  -> compiled C++ RobotRuntime
  -> ACK/NACK
```

The integration job checks out the current `main` branch of `VivekVRobo/Aurelia-Chan-Source` alongside the RCI pull-request revision, so contract drift between the repositories fails CI.

## Important boundary

RCI does not yet have the production RobotModel/Motion Planner stack. V004 therefore uses a small deterministic simulation pose mapping inside the integration test only. The synthetic joint/workspace envelope is explicitly test-only and uses `verified=True` solely to exercise the deterministic safety and gateway path in software.

Production `config/robot.yaml` and `config/servos.yaml` remain unverified and are not modified by V004. A green V004 run means the software integration path is compatible and the compiled firmware runtime returns the expected acknowledgement. It does not mean any physical joint, workspace, servo, power system, or E-stop wiring has been measured or validated.

## Terminal expectation

The compiled firmware runtime must first accept a host heartbeat and enter its ready state. It must then accept the structurally valid safety-authorized motion packet as `kMotionDeferred`, which maps to `ACK OK` while still performing zero actuator execution.

Physical actuation remains locked behind the later HIL milestone.
