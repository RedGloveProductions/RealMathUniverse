"""
Memory budget helper.

v0.1 uses estimated sizes from buffer declarations. Later this can query CUDA,
Metal, system memory, and disk output budgets before allocating.
"""

from __future__ import annotations


def estimate_field_bytes(resolution: tuple[int, int, int], field_count: int, bytes_per_value: int = 4) -> int:
    nx, ny, nz = resolution
    return int(nx * ny * nz * field_count * bytes_per_value)


def estimate_particle_bytes(particle_count: int, float_channels: int, int_channels: int = 1) -> int:
    return int(particle_count * ((float_channels * 4) + (int_channels * 4)))
