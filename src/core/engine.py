"""
RealMathUniverse engine loop.

v1.3B:
- Adds single particle source authority for geospatial crab particle fields.
- If particle_config.particles.initialization_mode == geospatial_crab_field,
  the engine allocates particle buffers from the real CSV row count instead of
  the execution profile's synthetic particle_count.
"""
from __future__ import annotations

from pathlib import Path

from src.core.frame_timer import FrameTimer


class RealMathUniverseEngine:
    def __init__(
        self,
        configs,
        profile,
        compute,
        buffer_registry,
        module_registry,
        diagnostics,
        headless: bool = False,
    ):
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.module_registry = module_registry
        self.diagnostics = diagnostics
        self.headless = headless
        self.dt = float(configs["universe_config"]["time"]["fixed_dt"])
        self.sim_time = 0.0
        self.frame_index = 0
        self.measured_frame_index = 0
        self.frame_timer = FrameTimer()
        self.warmup_frame_times_ms: list[float] = []
        self.last_physics_diagnostics: dict = {}
        self.particle_source_report: dict = {}

    def _resolve_particle_count(self) -> int:
        particle_cfg = self.configs.get("particle_config", {}).get("particles", {})
        mode = str(particle_cfg.get("initialization_mode", "deterministic_spiral_cloud"))
        if mode != "geospatial_crab_field":
            self.particle_source_report = {
                "version": "1.3B",
                "mode": mode,
                "authority": "execution_profile",
                "particle_count": int(self.profile.particle_count),
            }
            return int(self.profile.particle_count)

        source = particle_cfg.get(
            "geospatial_source_csv",
            "/Users/Joe/Documents/RealMathUniverse/data/raw/merged_navdata.csv",
        )
        try:
            from src.data.geospatial_particle_source import inspect_source

            report = inspect_source(Path(source))
            count = int(report.get("particle_count", 0))
            if count <= 0:
                raise ValueError(f"geospatial source contains no valid rows: {source}")
            report["authority"] = "geospatial_csv"
            report["profile_particle_count_overridden"] = int(self.profile.particle_count)
            report["engine_particle_count"] = count
            self.particle_source_report = report
            self.diagnostics.info(
                "v1.3B geospatial particle authority active: "
                f"count={count}, source={source}"
            )
            return count
        except Exception as exc:
            fallback = int(self.profile.particle_count)
            self.particle_source_report = {
                "version": "1.3B",
                "mode": mode,
                "authority": "fallback_execution_profile",
                "particle_count": fallback,
                "source_csv": str(source),
                "error": str(exc),
            }
            self.diagnostics.warn(
                "v1.3B geospatial particle authority failed; "
                f"falling back to profile particle_count={fallback}: {exc}"
            )
            return fallback

    def initialize(self) -> None:
        self.diagnostics.info("Allocating core GPU/array buffers...")
        dtype = self.compute.dtype_from_profile(self.profile.precision)
        n = self._resolve_particle_count()
        nx, ny, nz = self.profile.field_resolution
        self.buffer_registry.create("particle_positions", (n, 4), dtype)
        self.buffer_registry.create("particle_velocities", (n, 4), dtype)
        self.buffer_registry.create("particle_forces", (n, 4), dtype)
        self.buffer_registry.create("particle_mass", (n,), dtype)
        self.buffer_registry.create("particle_species", (n,), self.compute.int32_dtype)
        self.buffer_registry.create("curvature_grid", (nx, ny, nz), dtype)
        self.buffer_registry.create("higgs_grid", (nx, ny, nz), dtype)
        self.buffer_registry.create("temperature_grid", (nx, ny, nz), dtype)
        self.buffer_registry.create("probability_grid", (nx, ny, nz), dtype)
        self.buffer_registry.create("lambda_grid", (nx, ny, nz), dtype)
        self.module_registry.initialize_modules(headless=self.headless)
        self.diagnostics.info("Engine initialization complete.")

    def update(self, record_timing: bool = True) -> float:
        self.frame_timer.begin_frame()
        self.module_registry.update_modules(dt=self.dt, sim_time=self.sim_time)
        frame_ms = self.frame_timer.end_frame(record=record_timing)
        self.sim_time += self.dt
        self.frame_index += 1
        if record_timing:
            self.measured_frame_index += 1
        else:
            self.warmup_frame_times_ms.append(frame_ms)
        self.last_physics_diagnostics = self._collect_physics_diagnostics()
        if record_timing and (self.measured_frame_index == 1 or self.measured_frame_index % 300 == 0):
            self.diagnostics.info(
                "Measured physics diagnostics | "
                f"measured_frame={self.measured_frame_index} | "
                f"frame_ms={frame_ms:.3f} | "
                f"radius_mean={self.last_physics_diagnostics['radius_mean']:.6f} | "
                f"radius_min={self.last_physics_diagnostics['radius_min']:.6f} | "
                f"speed_mean={self.last_physics_diagnostics['speed_mean']:.6f}"
            )
        return frame_ms

    def reset_measured_timing(self) -> None:
        self.frame_timer.reset()
        self.measured_frame_index = 0
        self.diagnostics.info("Measured frame timer reset after warmup.")

    def shutdown(self) -> None:
        self.module_registry.shutdown_modules()
        stats = self.frame_timer.stats()
        self.diagnostics.info(
            f"Measured frame timing | count={stats.frame_count} "
            f"avg={stats.average_frame_ms:.3f}ms "
            f"min={stats.min_frame_ms:.3f}ms max={stats.max_frame_ms:.3f}ms "
            f"est_fps={stats.estimated_fps_from_average:.2f}"
        )
        self.diagnostics.info("Engine shutdown complete.")

    def diagnostics_payload(self) -> dict:
        warmup_avg = (
            sum(self.warmup_frame_times_ms) / len(self.warmup_frame_times_ms)
            if self.warmup_frame_times_ms
            else 0.0
        )
        return {
            "benchmark_mode": "warmup_then_measured",
            "headless": bool(self.headless),
            "total_frames_including_warmup": self.frame_index,
            "measured_frames": self.measured_frame_index,
            "particle_source_authority": self.particle_source_report,
            "warmup": {
                "frame_count": len(self.warmup_frame_times_ms),
                "average_frame_ms": warmup_avg,
                "max_frame_ms": max(self.warmup_frame_times_ms) if self.warmup_frame_times_ms else 0.0,
                "min_frame_ms": min(self.warmup_frame_times_ms) if self.warmup_frame_times_ms else 0.0,
            },
            "measured_frame_timing": self.frame_timer.stats().to_dict(),
            "last_physics_diagnostics": self.last_physics_diagnostics,
            "module_diagnostics": self._collect_module_diagnostics(),
        }

    def _collect_module_diagnostics(self) -> dict:
        payload = {}
        for name, module in self.module_registry.modules.items():
            if hasattr(module, "diagnostics_payload"):
                try:
                    payload[name] = module.diagnostics_payload()
                except Exception as exc:
                    payload[name] = {"error": str(exc)}
        return payload

    def _collect_physics_diagnostics(self) -> dict:
        xp = self.compute.xp
        positions = self.buffer_registry.get("particle_positions")
        velocities = self.buffer_registry.get("particle_velocities")
        forces = self.buffer_registry.get("particle_forces")
        pos3 = positions[:, 0:3]
        vel3 = velocities[:, 0:3]
        force3 = forces[:, 0:3]
        speed = xp.sqrt((vel3 * vel3).sum(axis=1))
        force_mag = xp.sqrt((force3 * force3).sum(axis=1))
        radius = xp.sqrt((pos3 * pos3).sum(axis=1) + 1.0e-9)
        return {
            "position_x_min": self.compute.to_float(xp.min(pos3[:, 0])),
            "position_x_max": self.compute.to_float(xp.max(pos3[:, 0])),
            "position_y_min": self.compute.to_float(xp.min(pos3[:, 1])),
            "position_y_max": self.compute.to_float(xp.max(pos3[:, 1])),
            "position_z_min": self.compute.to_float(xp.min(pos3[:, 2])),
            "position_z_max": self.compute.to_float(xp.max(pos3[:, 2])),
            "radius_min": self.compute.to_float(xp.min(radius)),
            "radius_mean": self.compute.to_float(xp.mean(radius)),
            "radius_max": self.compute.to_float(xp.max(radius)),
            "speed_mean": self.compute.to_float(xp.mean(speed)),
            "speed_max": self.compute.to_float(xp.max(speed)),
            "force_mean": self.compute.to_float(xp.mean(force_mag)),
            "force_max": self.compute.to_float(xp.max(force_mag)),
        }
