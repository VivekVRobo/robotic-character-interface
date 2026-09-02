"""Simulation-only semantic behavior profiles for the reference robot model."""

from __future__ import annotations

from dataclasses import dataclass

from rci.behavior.planner import BehaviorIntent
from rci.characters.contracts import MotionCue, MotionStyle
from rci.robotics.model import RobotModel


@dataclass(frozen=True, slots=True)
class EmbodiedBehaviorGoal:
    """Exact reference-model joint goal derived from actuator-free character semantics."""

    cue: MotionCue
    style: MotionStyle
    target_joints_deg: dict[str, float]


class SimulationBehaviorEmbodimentPlanner:
    """Map semantic cues to conservative predicted-model poses for software simulation only."""

    _OFFSETS: dict[MotionCue, dict[str, float]] = {
        MotionCue.LISTEN: {"base": 0.0, "shoulder": 5.0, "elbow": -5.0, "gripper": 0.0},
        MotionCue.ACKNOWLEDGE: {
            "base": 5.0,
            "shoulder": -5.0,
            "elbow": 10.0,
            "gripper": 0.0,
        },
        MotionCue.PRESENT: {
            "base": 20.0,
            "shoulder": -15.0,
            "elbow": -15.0,
            "gripper": 10.0,
        },
        MotionCue.CAUTION: {
            "base": -10.0,
            "shoulder": 10.0,
            "elbow": 15.0,
            "gripper": -5.0,
        },
        MotionCue.CELEBRATE: {
            "base": 0.0,
            "shoulder": -25.0,
            "elbow": -30.0,
            "gripper": 25.0,
        },
        MotionCue.THINK: {
            "base": -15.0,
            "shoulder": 15.0,
            "elbow": 5.0,
            "gripper": 0.0,
        },
    }
    _STYLE_SCALE = {
        MotionStyle.RESTRAINED: 0.5,
        MotionStyle.STANDARD: 0.75,
        MotionStyle.EXPRESSIVE: 1.0,
    }

    def __init__(self, model: RobotModel) -> None:
        if not model.profile.simulation_only or model.profile.hardware_verified:
            raise ValueError("simulation embodiment requires an unverified simulation-only profile")
        self.model = model

    def plan(self, intent: BehaviorIntent) -> EmbodiedBehaviorGoal:
        if intent.cue is MotionCue.NONE:
            raise ValueError("none cue has no embodied simulation goal")
        offsets = self._OFFSETS.get(intent.cue)
        if offsets is None:
            raise ValueError(f"no simulation embodiment profile for cue {intent.cue.value!r}")
        scale = self._STYLE_SCALE[intent.style]
        target = {
            name: round(self.model.home[name] + offsets[name] * scale, 2)
            for name in self.model.joint_names
        }
        self.model.validate_joint_positions(target)
        return EmbodiedBehaviorGoal(intent.cue, intent.style, target)
