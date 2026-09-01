# Digital Twin Robot Runtime

`rci.simulation.DigitalTwinRobot` is the software-only plant used when no physical robot is available.

It consumes only protocol-level `ValidatedMotionCommand` objects. It does not accept PWM values, servo pulse widths, or arbitrary actuator commands.

## Model

The plant uses the simulation-only reference robot profile and evolves every joint using deterministic acceleration- and velocity-limited motion. It also produces deterministic simulated current estimates and a simulated supply voltage. These values are **not physical measurements**.

## Telemetry

Protocol v1 `ROBOT_TELEMETRY` now carries:

- robot uptime;
- wire system state;
- flags;
- supply millivolts;
- per-joint protocol ID;
- position in centidegrees;
- velocity in centidegrees/second;
- current in milliamps.

The payload has matching Python and C++ golden-vector tests.

## E-stop

Calling the digital twin E-stop immediately freezes target motion, zeros simulated velocities, and reports the `ESTOP` wire state. Recovery requires an explicit reset call.

## Boundary

The digital twin is never included by `firmware/robot/robot.ino`. The normal firmware remains non-actuating until real HIL evidence exists. The digital twin exists so the rest of the application, telemetry UI, benchmarks, fault injection, and end-to-end orchestration can be completed now.
