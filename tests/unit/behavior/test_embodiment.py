from pathlib import Path

import pytest

from rci.behavior import BehaviorIntent, SimulationBehaviorEmbodimentPlanner
from rci.characters.contracts import MotionCue, MotionStyle
from rci.robotics.model import RobotModel
from rci.robotics.profile import load_reference_profile

ROOT = Path(__file__).resolve().parents[3]


def _model() -> RobotModel:
    return RobotModel(load_reference_profile(ROOT / "configs" / "simulation" / "reference_arm.yaml"))


def _intent(cue: MotionCue, style: MotionStyle = MotionStyle.RESTRAINED) -> BehaviorIntent:
    return BehaviorIntent(
        interaction_id="interaction",
        decision_id="decision",
        source_character="aurelia",
        expression="neutral",
        cue=cue,
        style=style,
    )


def test_all_semantic_cues_map_to_valid_simulation_joint_goals() -> None:
    model = _model()
    planner = SimulationBehaviorEmbodimentPlanner(model)

    for cue in MotionCue:
        if cue is MotionCue.NONE:
            continue
        goal = planner.plan(_intent(cue))
        model.validate_joint_positions(goal.target_joints_deg)
        assert set(goal.target_joints_deg) == set(model.joint_names)
        assert all(round(value * 100) == value * 100 for value in goal.target_joints_deg.values())

    assert model.profile.simulation_only is True
    assert model.profile.hardware_verified is False


def test_none_cue_has_no_simulation_pose() -> None:
    with pytest.raises(ValueError, match="none cue"):
        SimulationBehaviorEmbodimentPlanner(_model()).plan(_intent(MotionCue.NONE))
