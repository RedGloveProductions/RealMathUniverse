"""
OSC bridge placeholder.

VCV Rack is silent control/modulation first. v0.1 uses neutral fallback.
"""

from __future__ import annotations


class OSCBridgeModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics

    def initialize(self) -> None:
        cfg = self.configs["osc_config"]["osc"]
        if not cfg["enabled"]:
            self.diagnostics.info("OSC disabled. Neutral modulation fallback active.")
        else:
            self.diagnostics.info(
                f"OSC configured mode={cfg['mode']} receive_port={cfg['simulation_receive_port']}"
            )

    def update(self, dt: float, sim_time: float) -> None:
        return
