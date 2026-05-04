"""
Reduced GPU curvature solver.

This is not full numerical relativity. It is a v0.1 reduced curvature proxy:
    curvature_grid = softened / normalized mass-energy proxy

The goal is to establish GPU-resident curvature buffers from the beginning.
"""

from __future__ import annotations


class CurvatureReducedGPUSolver:
    def __init__(self, xp, strength: float = 1.0, softening: float = 1.0):
        self.xp = xp
        self.strength = float(strength)
        self.softening = float(softening)

    def step(self, curvature_grid, mass_energy_grid=None):
        if mass_energy_grid is None:
            # v0.1 placeholder: keep curvature finite and nonzero enough to prove updates.
            curvature_grid[...] = self.strength / (1.0 + self.softening)
        else:
            curvature_grid[...] = self.strength * mass_energy_grid / (self.softening + abs(mass_energy_grid))
        return curvature_grid
