"""Runnable software-complete simulation service entry point."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from rci.api import create_api_app
from rci.characters.client import AureliaCharacterClient
from rci.robotics.model import RobotModel
from rci.robotics.profile import default_reference_profile_path, load_reference_profile
from rci.simulation.runtime import SimulationRuntime


def build_app() -> FastAPI:
    """Build the simulation service without promoting predicted values to hardware evidence."""
    profile_path = Path(
        os.environ.get("RCI_REFERENCE_PROFILE", str(default_reference_profile_path()))
    ).expanduser()
    model = RobotModel(load_reference_profile(profile_path))
    runtime = SimulationRuntime(model)
    aurelia = AureliaCharacterClient(
        base_url=os.environ.get("AURELIA_URL", "http://127.0.0.1:5000")
    )
    app = create_api_app(aurelia, simulation_runtime=runtime)

    async def close_resources() -> None:
        await aurelia.close()
        await runtime.close()

    app.add_event_handler("shutdown", close_resources)
    return app


def main() -> None:
    """Launch the RCI simulation API and telemetry service."""
    uvicorn.run(
        build_app(),
        host=os.environ.get("RCI_HOST", "127.0.0.1"),
        port=int(os.environ.get("RCI_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
