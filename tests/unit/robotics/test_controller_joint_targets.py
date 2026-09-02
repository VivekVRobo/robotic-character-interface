from pathlib import Path

import pytest

from rci.robotics.controller import RobotController
from rci.robotics.model import RobotModel
from rci.robotics.profile import load_reference_profile

ROOT = Path(__file__).resolve().parents[3]


def test_joint_target_planning_preserves_exact_terminal_goal_and_pose() -> None:
    model = RobotModel(
        load_reference_profile(ROOT / "configs" / "simulation" / "reference_arm.yaml")
    )
    controller = RobotController(model)
    target = dict(model.home)
    target["base"] = 10.0
    target["shoulder"] = 25.0

    planned = controller.plan_joint_targets(
        current_joints_deg=model.home,
        target_joints_deg=target,
    )

    assert planned.target_joints_deg == target
    assert planned.trajectory.end.positions_deg == pytest.approx(target)
    expected_pose = controller.kinematics.forward(target)
    assert planned.target_pose.x_mm == pytest.approx(expected_pose.x_mm)
    assert planned.target_pose.y_mm == pytest.approx(expected_pose.y_mm)
    assert planned.target_pose.z_mm == pytest.approx(expected_pose.z_mm)
