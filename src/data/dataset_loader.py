"""
Dataset loader placeholder.

The engine must run without external datasets using synthetic defaults.
"""

from __future__ import annotations


class DatasetLoaderModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics

    def initialize(self) -> None:
        self.diagnostics.info("Dataset loader initialized. v0.1 uses synthetic defaults if no data is active.")

    def update(self, dt: float, sim_time: float) -> None:
        return
