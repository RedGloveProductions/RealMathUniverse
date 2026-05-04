"""
Solver registry.

Config declares solver names. Solver modules perform computation. This registry
connects those two ideas while enforcing strict physics mode.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


class SolverRegistry:
    def __init__(self, solver_config: dict[str, Any], profile, diagnostics):
        self.solver_config = solver_config
        self.profile = profile
        self.diagnostics = diagnostics
        self.loaded: dict[str, Any] = {}
        self.failed: dict[str, str] = {}

    def load_solvers(self) -> None:
        requested = self.solver_config.get("solvers", {})
        for solver_key, raw in requested.items():
            enabled = bool(raw.get("enabled", True))
            if not enabled:
                self.diagnostics.info(f"Solver disabled by config: {solver_key}")
                continue

            min_fidelity = raw.get("min_fidelity", "reduced")
            module_path = raw.get("module")
            class_name = raw.get("class")
            required = bool(raw.get("required", False))

            if not module_path or not class_name:
                self.failed[solver_key] = "Missing module or class field in solver_config."
                continue

            try:
                module = import_module(module_path)
                cls = getattr(module, class_name)
                self.loaded[solver_key] = cls
                self.diagnostics.info(
                    f"Loaded solver '{solver_key}' -> {module_path}.{class_name} "
                    f"(min_fidelity={min_fidelity})"
                )
            except Exception as exc:
                self.failed[solver_key] = str(exc)
                message = f"Failed to load solver '{solver_key}': {exc}"
                if required or self.profile.strict_physics_mode:
                    raise RuntimeError(message) from exc
                self.diagnostics.warn(message)

    def get(self, solver_key: str):
        if solver_key not in self.loaded:
            raise KeyError(f"Solver not loaded: {solver_key}")
        return self.loaded[solver_key]

    def describe(self) -> dict[str, Any]:
        return {
            "loaded": sorted(self.loaded.keys()),
            "failed": self.failed,
        }
