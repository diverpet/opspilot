"""Shared utilities for OpsPilot."""

import os
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=1)
def get_project_root() -> Path:
    """Get the project root directory.
    
    The project root is determined by:
    1. OPSPILOT_ROOT environment variable if set
    2. Walking up from the current file to find the directory containing pyproject.toml
    3. Falling back to current working directory
    
    Returns:
        Path to the project root directory
    """
    # Check environment variable first
    env_root = os.environ.get("OPSPILOT_ROOT")
    if env_root:
        return Path(env_root)
    
    # Try to find project root by looking for pyproject.toml
    current = Path(__file__).parent.parent.parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    
    # Fallback to current working directory
    return Path.cwd()


def get_data_dir() -> Path:
    """Get the data directory path."""
    return get_project_root() / "data"


def get_runbooks_dir() -> Path:
    """Get the runbooks directory path."""
    return get_project_root() / "runbooks"


def get_artifacts_dir() -> Path:
    """Get the artifacts directory path and ensure it exists."""
    artifacts_dir = get_project_root() / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    return artifacts_dir
