"""
Reduced black hole module placeholder.

Desktop/workstation versions can support:
    - event horizon radius
    - softened attraction
    - capture events
    - accretion swirl
    - time dilation scalar

v0.1 keeps the file present so configs and solver registry can reference it later.
"""

from __future__ import annotations


class BlackHoleReducedSolver:
    def __init__(self, xp, schwarzschild_radius: float = 1.0):
        self.xp = xp
        self.schwarzschild_radius = float(schwarzschild_radius)

    def capture_mask(self, distances):
        return distances <= self.schwarzschild_radius
