"""
Placeholder timekeeper for future variable timestep, fixed timestep, replay time,
dataset time, and staged activation time.
"""

from __future__ import annotations


class Timekeeper:
    def __init__(self, fixed_dt: float = 1.0 / 60.0):
        self.fixed_dt = fixed_dt
        self.time = 0.0
        self.frame = 0

    def tick(self) -> float:
        self.time += self.fixed_dt
        self.frame += 1
        return self.fixed_dt
