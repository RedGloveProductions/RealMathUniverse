"""
Base field interface concept.

Future field modules should support:
    initialize(config, state)
    deposit(particles, datasets, dt)
    update(dt, modulation_bus)
    sample(x, y, z)
    gradient(x, y, z)
    render_layer()
"""

from __future__ import annotations


class FieldModuleBase:
    def initialize(self):
        raise NotImplementedError

    def update(self, dt: float, sim_time: float):
        raise NotImplementedError
