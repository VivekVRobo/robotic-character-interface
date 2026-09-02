"""Runnable software-complete simulation service entry point."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from rci.api import create_api_app
from rci.characters.client import AureliaCharacterClient
from rci.robotics.model import RobotModel
from rci.robotics.profile import load_reference_profile
from rci.simulation.runtime import SimulationRuntime


def build_app() -> FastAPI:
    """Build the simulation service without promoting predicted values to hardware evidence."""
    profile_path = Path(
        os.environ.get("RCI_REFERENCE_PROFILE", "configs/simulation/reference_arm.yaml")
    ).expanduser()
    model = RobotModel(load_reference_profile(profile_path))
    runtime = SimulationRuntime(model)
    aurelia = AureliaCharacterClient(
        base_url=os.environ.get("AURELIA_URL", "http://127.0.0.1:5000")
    )
    return create_api_app(aurelia, simulation_runtime=runtime)


def main() -> None:
    """Launch the RCI simulation API and telemetry service."""
    uvicorn.run(
        build_app(),
        host=os.environ.get("RCI_HOST", "127.0.0.1"),
        port=int(os.environ.get("RCI_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
