"""
Probability field module.

Internal mode is the default. VCV/external mode will be detected later through
the modulation bus.
"""

from __future__ import annotations


class ProbabilityFieldGPUModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics

    def initialize(self) -> None:
        cfg = self.configs["probability_config"]["probability"]
        probability_grid = self.buffer_registry.get("probability_grid")
        probability_grid[...] = float(cfg["internal_default"])
        self.diagnostics.info("Probability field initialized in internal mode.")

    def update(self, dt: float, sim_time: float) -> None:
        return
