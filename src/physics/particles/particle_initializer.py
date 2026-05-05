"""
Particle initializer.

v1.3B:
- geospatial_crab_field initializes the actual solver particle buffers from
  merged_navdata.csv.
- deterministic_spiral_cloud remains as fallback/synthetic mode.
"""
from __future__ import annotations

import math
from pathlib import Path


class ParticleInitializer:
    def __init__(self, compute, buffer_registry, configs, diagnostics):
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.configs = configs
        self.diagnostics = diagnostics

    def initialize_cloud(self) -> None:
        cfg = self.configs["particle_config"]["particles"]
        mode = str(cfg.get("initialization_mode", "deterministic_spiral_cloud"))
        if mode == "geospatial_crab_field":
            try:
                self.initialize_geospatial_crab_field(cfg)
                return
            except Exception as exc:
                self.diagnostics.warn(
                    "Geospatial crab field initialization failed; "
                    f"falling back to deterministic spiral cloud: {exc}"
                )
        self.initialize_deterministic_spiral_cloud(cfg)

    def _to_backend_array(self, values, dtype):
        xp = self.compute.xp
        # torch, numpy, and cupy all support asarray with dtype in the project use cases.
        return xp.asarray(values, dtype=dtype)

    def initialize_geospatial_crab_field(self, cfg: dict) -> None:
        from src.data.geospatial_particle_source import load_geospatial_particles

        xp = self.compute.xp
        dtype = self.compute.float32_dtype
        source = Path(cfg.get("geospatial_source_csv", "/Users/Joe/Documents/RealMathUniverse/data/raw/merged_navdata.csv"))
        world_radius = float(cfg.get("geospatial_world_radius", 5.75))
        vertical_scale = float(cfg.get("geospatial_vertical_scale", 1.20))
        default_mass = float(cfg.get("default_sim_mass", 1.0))
        mass_density_scale = float(cfg.get("geospatial_mass_density_scale", 0.25))

        positions = self.buffer_registry.get("particle_positions")
        velocities = self.buffer_registry.get("particle_velocities")
        forces = self.buffer_registry.get("particle_forces")
        masses = self.buffer_registry.get("particle_mass")
        species = self.buffer_registry.get("particle_species")

        data = load_geospatial_particles(
            source_csv=source,
            world_radius=world_radius,
            vertical_scale=vertical_scale,
            default_mass=default_mass,
            mass_density_scale=mass_density_scale,
        )
        n_buffer = int(positions.shape[0])
        n_data = int(data.count)
        n = min(n_buffer, n_data)
        if n <= 0:
            raise ValueError("No geospatial particles available for solver buffers.")

        pos_arr = self._to_backend_array(data.positions[:n], dtype)
        vel_arr = self._to_backend_array(data.velocities[:n], dtype)
        mass_arr = self._to_backend_array(data.masses[:n], dtype)

        positions[:n, :] = pos_arr
        velocities[:n, :] = vel_arr
        forces[:n, :] = 0.0
        masses[:n] = mass_arr
        species[:n] = 0

        if n < n_buffer:
            # Should not usually happen in v1.3B because engine allocates exact row count,
            # but keep the remainder harmless if a profile cap is later introduced.
            positions[n:, :] = 0.0
            velocities[n:, :] = 0.0
            forces[n:, :] = 0.0
            masses[n:] = default_mass
            species[n:] = 0

        try:
            from src.data.geospatial_particle_source import atomic_write_json, STATE_OUT

            state = dict(data.stats)
            state.update({
                "live_authority": "python_solver_buffers",
                "buffer_count": n_buffer,
                "loaded_count": n,
                "status": "solver_buffers_initialized",
                "version": "1.3B",
            })
            atomic_write_json(STATE_OUT, state)
        except Exception:
            pass

        self.diagnostics.info(
            "ParticleInitializer loaded geospatial crab field into solver buffers: "
            f"count={n}, source={source}, world_radius={world_radius}, vertical_scale={vertical_scale}"
        )

    def initialize_deterministic_spiral_cloud(self, cfg: dict) -> None:
        xp = self.compute.xp
        dtype = self.compute.float32_dtype
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
        velocities[:, 0] = -xp.sin(angle) * swirl_velocity
        velocities[:, 1] = 0.0
        velocities[:, 2] = xp.cos(angle) * swirl_velocity
        velocities[:, 3] = 0.0
        forces[...] = 0.0
        masses[...] = default_mass
        species[...] = 0
        self.diagnostics.info(
            "ParticleInitializer created deterministic 3D cloud: "
            f"count={n}, radius={radius}, vertical_scale={vertical_scale}"
        )


