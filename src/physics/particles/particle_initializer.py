"""
Particle initializer for v0.2A.

Purpose:
    Generate a deterministic 3D particle cloud directly on the active backend.

The pattern is a compact spiral/shell distribution. It is not random, which
makes repeated runs easier to compare.
"""

from __future__ import annotations

import math


class ParticleInitializer:
    def __init__(self, compute, buffer_registry, configs, diagnostics):
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.configs = configs
        self.diagnostics = diagnostics

    def initialize_cloud(self) -> None:
        xp = self.compute.xp
        dtype = self.compute.float32_dtype
        cfg = self.configs["particle_config"]["particles"]

        positions = self.buffer_registry.get("particle_positions")
        velocities = self.buffer_registry.get("particle_velocities")
        forces = self.buffer_registry.get("particle_forces")
        masses = self.buffer_registry.get("particle_mass")
        species = self.buffer_registry.get("particle_species")

        n = positions.shape[0]
        radius = float(cfg.get("initial_cloud_radius", 5.0))
        vertical_scale = float(cfg.get("initial_cloud_vertical_scale", 1.0))
        swirl_velocity = float(cfg.get("initial_swirl_velocity", 0.04))
        default_mass = float(cfg.get("default_sim_mass", 1.0))

        t = xp.linspace(0.0, 1.0, num=n, dtype=dtype)
        angle = t * (math.pi * 2.0 * 13.0)
        radial = radius * (0.15 + 0.85 * t)

        x = radial * xp.cos(angle)
        y = vertical_scale * radius * (t - 0.5)
        z = radial * xp.sin(angle)

        positions[:, 0] = x
        positions[:, 1] = y
        positions[:, 2] = z
        positions[:, 3] = 1.0

        # Tangential initial velocity around the y-axis.
        velocities[:, 0] = -xp.sin(angle) * swirl_velocity
        velocities[:, 1] = 0.0
        velocities[:, 2] = xp.cos(angle) * swirl_velocity
        velocities[:, 3] = 0.0

        forces[...] = 0.0
        masses[...] = default_mass
        species[...] = 0

        self.diagnostics.info(
            f"ParticleInitializer created deterministic 3D cloud: "
            f"count={n}, radius={radius}, vertical_scale={vertical_scale}"
        )
