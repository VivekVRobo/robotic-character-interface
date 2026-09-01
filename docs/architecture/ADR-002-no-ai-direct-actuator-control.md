# ADR-002: No AI Direct Actuator Control

**Status:** Accepted

AI/cognition/character components return structured semantic responses only. They cannot emit or transmit raw PWM/servo commands. Motion must pass behavior -> robotics -> deterministic safety -> robot gateway -> MCU safety.
