"""
RealMathUniverse v1.1B
Dataset Mode Manager

Runtime control is file-based so data mode can be switched without changing the
VCV bridge or the Metal renderer contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import time


class DatasetModeManager:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.config_path = self.project_root / "config" / "dataset_mode_config.json"
        self.config = self._load_json(self.config_path, {})
        self.runtime_state_file = self.project_root / self.config.get("runtime_state_file", "runtime/data_mode_state.json")
        self.runtime_state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.runtime_state_file.exists():
            self.write_state({
                "version": "1.1B",
                "enabled": bool(self.config.get("enabled_default", True)),
                "mode": self.config.get("mode_default", "crab_nav_csv"),
                "updated_by": "dataset_mode_manager_default",
                "timestamp_unix": time.time(),
            })

    @staticmethod
    def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return dict(default)
        return dict(default)

    def read_state(self) -> Dict[str, Any]:
        return self._load_json(self.runtime_state_file, {
            "version": "1.1B",
            "enabled": bool(self.config.get("enabled_default", True)),
            "mode": self.config.get("mode_default", "crab_nav_csv"),
            "timestamp_unix": time.time(),
        })

    def write_state(self, state: Dict[str, Any]) -> None:
        self.runtime_state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.runtime_state_file.with_suffix(self.runtime_state_file.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
        tmp.replace(self.runtime_state_file)

    def set_enabled(self, enabled: bool, updated_by: str = "manual") -> Dict[str, Any]:
        state = self.read_state()
        state.update({
            "version": "1.1B",
            "enabled": bool(enabled),
            "updated_by": updated_by,
            "timestamp_unix": time.time(),
        })
        self.write_state(state)
        return state

    def toggle(self, updated_by: str = "manual") -> Dict[str, Any]:
        state = self.read_state()
        return self.set_enabled(not bool(state.get("enabled", True)), updated_by=updated_by)
