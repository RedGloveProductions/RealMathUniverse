"""
High-fidelity geodesic solver placeholder.

This file intentionally exists but does not claim to implement full GR yet.
Strict high-fidelity profiles can require this module, while its actual methods
will be expanded as the math stack develops.
"""

from __future__ import annotations


class GeodesicSolverHighFidelity:
    def __init__(self, xp):
        self.xp = xp

    def step(self, *args, **kwargs):
        raise NotImplementedError(
            "High-fidelity geodesic integration is reserved for later versions."
        )
