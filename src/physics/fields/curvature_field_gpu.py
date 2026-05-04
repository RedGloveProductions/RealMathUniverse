"""
Curvature field module.

v0.2E:
    Builds an active 3D curvature field instead of just a constant diagnostic
    value. Particle solver samples this grid to modulate force response.

This remains a reduced model. It is not full GR.
"""

from __future__ import annotations


class CurvatureFieldGPUModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics
        self.initialized_pattern = False

    def initialize(self) -> None:
        self._write_curvature_pattern(sim_time=0.0)
        self.diagnostics.info("Curvature field initialized with active 3D sampling pattern for v0.2E.")

    def update(self, dt: float, sim_time: float) -> None:
        cfg = self.configs["field_config"].get("sampling_stress", {})
        if bool(cfg.get("animate_fields", False)):
            self._write_curvature_pattern(sim_time=sim_time)

    def _write_curvature_pattern(self, sim_time: float) -> None:
        xp = self.compute.xp
        grid = self.buffer_registry.get("curvature_grid")
        nx, ny, nz = grid.shape

        cfg = self.configs["field_config"].get("sampling_stress", {})
        strength = float(cfg.get("curvature_pattern_strength", 1.0))
        radius_scale = float(cfg.get("curvature_pattern_radius_scale", 0.35))
        wave_mix = float(cfg.get("curvature_wave_mix", 0.15))

        x = xp.linspace(-1.0, 1.0, num=nx, dtype=self.compute.float32_dtype)
        y = xp.linspace(-1.0, 1.0, num=ny, dtype=self.compute.float32_dtype)
        z = xp.linspace(-1.0, 1.0, num=nz, dtype=self.compute.float32_dtype)

        # Broadcasting creates a 3D potential well plus mild wave structure.
        xx = x[:, None, None]
        yy = y[None, :, None]
        zz = z[None, None, :]

        r2 = xx * xx + yy * yy + zz * zz
        well = strength / (1.0 + r2 / max(radius_scale * radius_scale, 1e-6))
        wave = wave_mix * xp.sin((xx * 7.0) + (zz * 5.0) + float(sim_time))
        grid[...] = well + wave
