# Software Inputs and API Boundary

This milestone completes the software-only human-input boundary without claiming unavailable sensors or physical robot control.

```text
text -------------------\
simulated voice --------+-> MultimodalCorrelator -> MeaningFrame
MPU6050 motion gesture -/                         |
                                                  v
                                      AureliaCharacterClient
                                                  |
                                 rci.character_response.v1
                                                  |
                                                  v
                                         BehaviorPlanner
                                                  |
                                       semantic behavior only
```

## Gesture scope

The V1 classifier uses MPU6050-style pitch, roll, and angular-rate telemetry. It can recognize motion patterns such as tilt, flick, rotation, wave, and hold. It does not infer fist, open-palm, pointing, or other finger poses because the assumed V1 hardware has no finger sensors.

Synthetic traces are marked as simulation evidence.

## Voice scope

The voice service defines deterministic VAD, transcript, speech-planning, and barge-in state behavior. The current backend is explicitly a simulation backend: it does not claim microphone capture, speech-recognition accuracy, human audio, or physical speaker playback.

## Character boundary

RCI calls Aurelia through the hardened `/api/cognitive-cycle` endpoint. A response is accepted only when the top-level cycle is safe to publish and the embedded `rci.character_response.v1` passes RCI's strict consumer contract. Unverified, uncommitted, malformed, or actuator-polluted responses fail closed.

## HTTP API boundary

`/api/simulation/interact` is intentionally simulation-only. It can return:

- the correlated `MeaningFrame`,
- the verified character response,
- optional actuator-free semantic behavior.

It cannot return or construct `MotionAuthorization`, `ValidatedMotionCommand`, PWM values, servo writes, or joint wire commands. Motion authorization remains exclusively downstream of deterministic robotics and safety layers.

`/api/status` explicitly reports `hardware_verified: false` and `physical_motion_enabled: false` until real hardware evidence changes those facts.
