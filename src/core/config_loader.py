"""
Config loader for RealMathUniverse.

3P:
    Purpose:
        Load JSON configuration files from config/.
    Process:
        Read all *.json files, parse them, and return a dictionary keyed by stem.
    Product:
        A configs dictionary used by main.py, registries, solvers, and modules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigLoader:
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)

    def load_json(self, filename: str) -> dict[str, Any]:
        path = self.config_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required config file: {path}")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def load_all_json(self) -> dict[str, dict[str, Any]]:
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory does not exist: {self.config_dir}")

        configs: dict[str, dict[str, Any]] = {}
        for path in sorted(self.config_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as f:
                configs[path.stem] = json.load(f)

        required = [
            "execution_profiles",
            "gpu_config",
            "solver_config",
            "module_config",
            "universe_config",
            "render_config",
            "camera_config",
            "relativity_config",
            "field_config",
            "particle_config",
            "probability_config",
            "osc_config",
            "dataset_config",
            "calibration_maps",
            "fluid_config",
        ]
        missing = [name for name in required if name not in configs]
        if missing:
            raise FileNotFoundError(f"Missing required configs: {missing}")

        return configs
