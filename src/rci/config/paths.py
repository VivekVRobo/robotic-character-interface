"""Configuration path resolution."""

from pathlib import Path


def default_config_dir() -> Path:
    """Resolve the repository-local config directory from the current process."""
    return Path("configs").resolve()
