"""Robot model, kinematics, trajectory planning, and simulation controller."""

from rci.robotics.controller import PlannedMotion, RobotController
from rci.robotics.kinematics import Kinematics, KinematicsError
from rci.robotics.model import RobotModel, RobotModelError
from rci.robotics.models import (
    AssumptionProvenance,
    CartesianPose,
    JointSolution,
    JointTrajectory,
    ReferenceGeometry,
    ReferenceJoint,
    ReferenceRobotProfile,
    TrajectorySample,
    WorkspaceEstimate,
)
from rci.robotics.profile import ReferenceProfileError, load_reference_profile
from rci.robotics.trajectory import TrajectoryError, TrajectoryGenerator

__all__ = [
    "AssumptionProvenance",
    "CartesianPose",
    "JointSolution",
    "JointTrajectory",
    "Kinematics",
    "KinematicsError",
    "PlannedMotion",
    "ReferenceGeometry",
    "ReferenceJoint",
    "ReferenceProfileError",
    "ReferenceRobotProfile",
    "RobotController",
    "RobotModel",
    "RobotModelError",
    "TrajectoryError",
    "TrajectoryGenerator",
    "TrajectorySample",
    "WorkspaceEstimate",
    "load_reference_profile",
]
