"""
Temperature field module.

v0.1 creates a constant baseline temperature field. Dataset-to-temperature
mappings will be routed through calibration maps later.
"""

from __future__ import annotations


class TemperatureFieldGPUModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics

    def initialize(self) -> None:
        cfg = self.configs["field_config"]["temperature"]
        temperature_grid = self.buffer_registry.get("temperature_grid")
        temperature_grid[...] = float(cfg["baseline_temperature"])
        self.diagnostics.info("Temperature field initialized.")

    def update(self, dt: float, sim_time: float) -> None:
        return
