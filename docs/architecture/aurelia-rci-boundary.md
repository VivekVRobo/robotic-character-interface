# Aurelia -> RCI Character Boundary

Aurelia emits the versioned `rci.character_response.v1` semantic contract. RCI validates it again before behavior planning.

The contract includes verified speech, canonical expression, and an optional high-level motion cue such as `present`, `listen`, or `caution`. It contains no actuator-level control fields. Motion disposition is only `none` or `optional`; character intelligence cannot require physical motion.

```text
Aurelia Cognitive OS
  -> verified CharacterResponse v1
  -> RCI strict contract validation
  -> Behavior Planner
  -> Motion Request
  -> Trajectory Planner
  -> Motion Safety Supervisor
  -> ValidatedMotionCommand
  -> Robot Gateway / MCU
```

The semantic contract and binary robot protocol are deliberately separate. A character response cannot be serialized directly into a robot command. Only the deterministic robotics/safety pipeline may construct `VALIDATED_MOTION_COMMAND` protocol messages.
