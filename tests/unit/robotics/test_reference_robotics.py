from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from rci.domain.enums import SystemState
from rci.robotics import (
    CartesianPose,
    Kinematics,
    KinematicsError,
    ReferenceRobotProfile,
    RobotController,
    RobotModel,
    TrajectoryError,
    TrajectoryGenerator,
    load_reference_profile,
)

ROOT = Path(__file__).resolve().parents[3]
PROFILE = ROOT / "configs" / "simulation" / "reference_arm.yaml"


def _model() -> RobotModel:
    return RobotModel(load_reference_profile(PROFILE))


def test_reference_profile_is_explicitly_simulation_only_and_unverified() -> None:
    profile = load_reference_profile(PROFILE)
    assert profile.simulation_only is True
    assert profile.hardware_verified is False
    assert profile.provenance.source == "engineering_prediction"

    raw = profile.model_dump()
    raw["hardware_verified"] = True
    with pytest.raises(ValidationError):
        ReferenceRobotProfile.model_validate(raw)


def test_forward_inverse_round_trip_for_reachable_pose() -> None:
    model = _model()
    kinematics = Kinematics(model)
    joints = {"base": 25.0, "shoulder": 35.0, "elbow": 45.0, "gripper": 20.0}

    pose = kinematics.forward(joints)
    solved = kinematics.inverse(pose, gripper_deg=20.0, seed_deg=joints)
    solved_pose = kinematics.forward(solved.as_dict())

    assert solved_pose.x_mm == pytest.approx(pose.x_mm, abs=1e-6)
    assert solved_pose.y_mm == pytest.approx(pose.y_mm, abs=1e-6)
    assert solved_pose.z_mm == pytest.approx(pose.z_mm, abs=1e-6)


def test_inverse_kinematics_rejects_unreachable_target() -> None:
    with pytest.raises(KinematicsError, match="outside the reference arm reach"):
        Kinematics(_model()).inverse(CartesianPose(x_mm=1000.0, y_mm=0.0, z_mm=80.0))


def test_workspace_is_computed_from_kinematics_not_claimed_as_measured() -> None:
    estimate = Kinematics(_model()).estimate_workspace(samples_per_joint=5)
    assert estimate.samples == 125
    assert estimate.min_x_mm < estimate.max_x_mm
    assert estimate.min_y_mm < estimate.max_y_mm
    assert estimate.min_z_mm < estimate.max_z_mm


def test_trajectory_respects_predicted_velocity_and_acceleration_limits() -> None:
    model = _model()
    generator = TrajectoryGenerator(model)
    start = model.home
    target = {**start, "base": 45.0, "shoulder": 55.0, "elbow": 20.0}

    trajectory = generator.generate(start, target, sample_period_s=0.01)
    assert trajectory.start.positions_deg == pytest.approx(start)
    assert trajectory.end.positions_deg == pytest.approx(target)

    for sample in trajectory.samples:
        for name, velocity in sample.velocities_deg_s.items():
            assert abs(velocity) <= model.profile.joints[name].max_velocity_deg_s + 1e-9
        for name, acceleration in sample.accelerations_deg_s2.items():
            assert abs(acceleration) <= model.profile.joints[name].max_acceleration_deg_s2 + 1e-9


def test_trajectory_rejects_duration_below_bounded_minimum() -> None:
    model = _model()
    generator = TrajectoryGenerator(model)
    target = {**model.home, "base": 90.0}
    minimum = generator.minimum_duration(model.home, target)
    with pytest.raises(TrajectoryError, match="below bounded minimum"):
        generator.generate(model.home, target, duration_s=minimum / 2.0)


def test_controller_outputs_existing_safety_contract_without_authorizing_hardware() -> None:
    model = _model()
    controller = RobotController(model)
    current = model.home
    target = Kinematics(model).forward({**current, "base": 20.0, "shoulder": 40.0})

    planned = controller.plan_cartesian(current_joints_deg=current, target_pose=target)
    candidate, dynamics = planned.terminal_safety_inputs(
        system_state=SystemState.ARMED,
        estop_active=False,
        command_age_ms=0.0,
        heartbeat_age_ms=0.0,
    )

    assert candidate.system_state is SystemState.ARMED
    assert candidate.estop_active is False
    assert set(candidate.joint_targets_deg) == {"base", "shoulder", "elbow", "gripper"}
    assert candidate.workspace_point_mm is not None
    assert dynamics.command_age_ms == 0.0
    assert dynamics.heartbeat_age_ms == 0.0
    assert model.profile.hardware_verified is False
