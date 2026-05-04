"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse Field Sampler
Version: 0.2E

Purpose:
    Sample GPU-resident 3D fields at particle positions.

Current method:
    Nearest-neighbor grid sampling.

Why nearest first:
    It is simple, fast, deterministic, and useful for benchmarking. Later
    versions can add trilinear sampling.
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations


class FieldSamplerGPU:
    def __init__(self, compute):
        self.compute = compute
        self.xp = compute.xp

    def sample_nearest(self, field_grid, positions_xyz, world_radius: float):
        """
        Map world coordinates in [-world_radius, +world_radius] into grid indices.
        Returns sampled scalar values, one per particle.
        """
        xp = self.xp
        nx, ny, nz = field_grid.shape

        radius = float(world_radius)
        if radius <= 0:
            radius = 1.0

        normalized = (positions_xyz + radius) / (2.0 * radius)
        normalized = xp.clamp(normalized, min=0.0, max=0.999999)

        ix = xp.astype(xp.floor(normalized[:, 0] * nx), self.compute.int64_dtype)
        iy = xp.astype(xp.floor(normalized[:, 1] * ny), self.compute.int64_dtype)
        iz = xp.astype(xp.floor(normalized[:, 2] * nz), self.compute.int64_dtype)

        return field_grid[ix, iy, iz]
