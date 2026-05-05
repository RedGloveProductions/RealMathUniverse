"""
RealMathUniverse Particle Solver

v1.3B:
- Reads runtime_state.json and control_state.json as a unified runtime control layer.
- Honors geospatial startup pause: when simulation_paused is true, the solver leaves
  geospatial particles fixed and only renderer/export updates continue.
- Keeps behavior_mode persistence support through control_state/behavior_state bridge.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.physics.fields.field_sampler_gpu import FieldSamplerGPU
from src.physics.particles.particle_initializer import ParticleInitializer


class ParticleSolverGPUModule:
    def __init__(self, name, configs, profile, compute, buffer_registry, solver_registry, diagnostics):
        self.name = name
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.solver_registry = solver_registry
        self.diagnostics = diagnostics
        self.center = None
        self.sampler = None
        self.capture_count_total = 0
        self.respawn_count_total = 0
        self.last_capture_count = 0
        self.last_min_radius = 0.0
        self.last_mean_radius = 0.0
        self.project_root = Path(__file__).resolve().parents[3]
        self.control_state_path = self.project_root / "output" / "control_state.json"
        self.runtime_state_path = self.project_root / "output" / "runtime_state.json"
        self.control_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.control_state_mtime = 0.0
        self.runtime_state_mtime = 0.0
        self.live_control_state = {}
        self.runtime_state = {}
        self.last_paused_state = None

    def initialize(self) -> None:
        initializer = ParticleInitializer(
            compute=self.compute,
            buffer_registry=self.buffer_registry,
            configs=self.configs,
            diagnostics=self.diagnostics,
        )
        initializer.initialize_cloud()
        center_cfg = self.configs["relativity_config"]["curvature"].get("center", [0.0, 0.0, 0.0])
        self.center = self.compute.xp.asarray(center_cfg, dtype=self.compute.float32_dtype)
        self.sampler = FieldSamplerGPU(self.compute)
        self._load_live_control_state(force=True)
        behavior = self._collapse_config().get("behavior_mode", "stable_orbit_cloud")
        self.diagnostics.info(f"Particle solver initialized for v1.3B single-source geospatial authority. behavior={behavior}")

    def update(self, dt: float, sim_time: float) -> None:
        self._load_live_control_state(force=False)
        xp = self.compute.xp
        collapse_cfg = self._collapse_config()
        positions = self.buffer_registry.get("particle_positions")
        velocities = self.buffer_registry.get("particle_velocities")
        forces = self.buffer_registry.get("particle_forces")

        pos3 = positions[:, 0:3]
        vel3 = velocities[:, 0:3]
        force3 = forces[:, 0:3]

        if self._simulation_is_paused():
            # Geospatial startup must be a stable readable map, not a physics run.
            vel3[...] = 0.0
            force3[...] = 0.0
            radius = xp.sqrt(((pos3 - self.center) * (pos3 - self.center)).sum(axis=1) + 1.0e-9)
            self.last_capture_count = 0
            self.last_min_radius = self.compute.to_float(xp.min(radius))
            self.last_mean_radius = self.compute.to_float(xp.mean(radius))
            if self.last_paused_state is not True:
                self.diagnostics.info("v1.3B geospatial solver paused: particles fixed, forces disabled.")
                self.last_paused_state = True
            return
        if self.last_paused_state is not False:
            self.diagnostics.info("v1.3B geospatial solver running: physics armed.")
            self.last_paused_state = False

        cfg = self.configs["relativity_config"]["curvature"]
        sample_cfg = self.configs["field_config"].get("sampling_stress", {})
        masses = self.buffer_registry.get("particle_mass")
        curvature_grid = self.buffer_registry.get("curvature_grid")
        higgs_grid = self.buffer_registry.get("higgs_grid")
        temperature_grid = self.buffer_registry.get("temperature_grid")
        probability_grid = self.buffer_registry.get("probability_grid")

        behavior_mode = str(collapse_cfg.get("behavior_mode", "stable_orbit_cloud"))
        minimum_radius = float(collapse_cfg.get("minimum_radius", 0.20))
        capture_radius = float(collapse_cfg.get("capture_radius", 0.08))
        event_horizon_visual_radius = float(collapse_cfg.get("event_horizon_visual_radius", 0.35))
        core_pressure_strength = float(collapse_cfg.get("core_pressure_strength", 0.12))
        core_pressure_radius = float(collapse_cfg.get("core_pressure_radius", 0.85))
        orbital_floor_velocity = float(collapse_cfg.get("orbital_floor_velocity", 0.025))
        angular_momentum_preservation = float(collapse_cfg.get("angular_momentum_preservation", 0.10))
        respawn_radius = float(collapse_cfg.get("respawn_radius", 5.2))
        respawn_on_capture = bool(collapse_cfg.get("respawn_on_capture", False))
        strength = float(cfg.get("particle_coupling_strength", 0.25))
        softening = float(cfg.get("particle_softening", 0.75))
        damping = float(cfg.get("velocity_damping", 0.999))
        max_force = float(cfg.get("max_force", 2.0))
        world_radius = float(sample_cfg.get("world_radius", 6.0))
        curvature_sample_weight = float(sample_cfg.get("curvature_sample_weight", 1.0))
        higgs_sample_weight = float(sample_cfg.get("higgs_sample_weight", 0.15))
        temperature_sample_weight = float(sample_cfg.get("temperature_sample_weight", 0.05))
        probability_sample_weight = float(sample_cfg.get("probability_sample_weight", 0.10))

        curvature_sample = self.sampler.sample_nearest(curvature_grid, pos3, world_radius)
        higgs_sample = self.sampler.sample_nearest(higgs_grid, pos3, world_radius)
        temperature_sample = self.sampler.sample_nearest(temperature_grid, pos3, world_radius)
        probability_sample = self.sampler.sample_nearest(probability_grid, pos3, world_radius)
        delta = self.center - pos3
        dist2 = (delta * delta).sum(axis=1) + softening * softening
        radius = xp.sqrt((delta * delta).sum(axis=1) + 1.0e-9)
        inv_radius = 1.0 / radius
        direction_in = delta * inv_radius[:, None]
        direction_out = -direction_in
        field_modulation = (
            1.0
            + curvature_sample_weight * curvature_sample
            + higgs_sample_weight * xp.abs(higgs_sample)
            + temperature_sample_weight * temperature_sample
            + probability_sample_weight * probability_sample
        )
        force_mag = (strength * field_modulation) / dist2
        force_mag = xp.clamp(force_mag, min=-max_force, max=max_force)
        force3[...] = direction_in * force_mag[:, None]
        if behavior_mode in ("stable_orbit_cloud", "accretion_disk", "field_pressure_bounce"):
            pressure_factor = xp.clamp((core_pressure_radius - radius) / max(core_pressure_radius, 1.0e-6), min=0.0, max=1.0)
            pressure_force = core_pressure_strength * pressure_factor * pressure_factor
            force3[...] = force3 + direction_out * pressure_force[:, None]
        if behavior_mode == "field_pressure_bounce":
            bounce_factor = xp.clamp((minimum_radius * 2.0 - radius) / max(minimum_radius * 2.0, 1.0e-6), min=0.0, max=1.0)
            force3[...] = force3 + direction_out * (core_pressure_strength * 2.5 * bounce_factor)[:, None]

        inv_mass = 1.0 / masses
        acceleration = force3 * inv_mass[:, None]
        vel3[...] = (vel3 + acceleration * dt) * damping
        if behavior_mode in ("stable_orbit_cloud", "accretion_disk"):
            self._apply_orbital_floor(pos3, vel3, radius, orbital_floor_velocity, angular_momentum_preservation)
        if behavior_mode == "accretion_disk":
            vel3[:, 1] = vel3[:, 1] * 0.92
            pos3[:, 1] = pos3[:, 1] * 0.998
        pos3[...] = pos3 + vel3 * dt
        delta_after = self.center - pos3
        radius_after = xp.sqrt((delta_after * delta_after).sum(axis=1) + 1.0e-9)
        if behavior_mode in ("stable_orbit_cloud", "accretion_disk", "field_pressure_bounce"):
            self._enforce_minimum_radius(pos3, radius_after, minimum_radius)
        capture_mask = radius_after < capture_radius
        self.last_capture_count = self._count_mask(capture_mask)
        self.capture_count_total += self.last_capture_count
        if respawn_on_capture and self.last_capture_count > 0:
            self._respawn_captured(pos3, vel3, capture_mask, respawn_radius)
            self.respawn_count_total += self.last_capture_count
        elif behavior_mode == "black_hole_capture" and self.last_capture_count > 0:
            self._place_captured_on_horizon(pos3, vel3, capture_mask, event_horizon_visual_radius)
        self.last_min_radius = self.compute.to_float(xp.min(radius_after))
        self.last_mean_radius = self.compute.to_float(xp.mean(radius_after))

    def diagnostics_payload(self) -> dict:
        return {
            "version": "1.3B",
            "capture_count_total": int(self.capture_count_total),
            "respawn_count_total": int(self.respawn_count_total),
            "last_capture_count": int(self.last_capture_count),
            "last_min_radius": float(self.last_min_radius),
            "last_mean_radius": float(self.last_mean_radius),
            "control_state_path": str(self.control_state_path),
            "runtime_state_path": str(self.runtime_state_path),
            "runtime_state": self.runtime_state,
            "simulation_paused": bool(self._simulation_is_paused()),
            "physics_armed": bool(self._physics_is_armed()),
            "live_control_state": self.live_control_state,
            "collapse_behavior": self._collapse_config(),
        }

    def _read_json_if_changed(self, path: Path, last_mtime: float, force: bool = False):
        if not path.exists():
            return None, last_mtime
        try:
            mtime = path.stat().st_mtime
            if not force and mtime == last_mtime:
                return None, last_mtime
            with path.open("r", encoding="utf-8") as f:
                state = json.load(f)
            if isinstance(state, dict):
                return state, mtime
        except Exception as exc:
            self.diagnostics.warn(f"Could not read runtime/control state {path}: {exc}")
        return None, last_mtime

    def _load_live_control_state(self, force: bool = False) -> None:
        runtime, self.runtime_state_mtime = self._read_json_if_changed(self.runtime_state_path, self.runtime_state_mtime, force=force)
        control, self.control_state_mtime = self._read_json_if_changed(self.control_state_path, self.control_state_mtime, force=force)
        changed = False
        if runtime is not None:
            self.runtime_state = runtime
            changed = True
        if control is not None:
            merged = dict(control)
            # Runtime state has authority for pause/armed/geospatial mode.
            if isinstance(self.runtime_state, dict):
                for key in (
                    "runtime_mode", "geospatial_enabled", "simulation_paused", "physics_armed",
                    "particle_source_mode", "spacebar_mode"
                ):
                    if key in self.runtime_state:
                        merged[key] = self.runtime_state[key]
            self.live_control_state = merged
            changed = True
        elif runtime is not None:
            merged = dict(self.live_control_state) if isinstance(self.live_control_state, dict) else {}
            for key in (
                "runtime_mode", "geospatial_enabled", "simulation_paused", "physics_armed",
                "particle_source_mode", "spacebar_mode"
            ):
                if key in self.runtime_state:
                    merged[key] = self.runtime_state[key]
            self.live_control_state = merged
            changed = True
        if changed:
            self.diagnostics.info(f"Loaded v1.3B live runtime/control state: {self.live_control_state}")

    def _physics_is_armed(self) -> bool:
        live = self.live_control_state if isinstance(self.live_control_state, dict) else {}
        runtime_mode = str(live.get("runtime_mode", ""))
        if runtime_mode == "geospatial_crab_field":
            return bool(live.get("physics_armed", False))
        return True

    def _simulation_is_paused(self) -> bool:
        live = self.live_control_state if isinstance(self.live_control_state, dict) else {}
        runtime_mode = str(live.get("runtime_mode", ""))
        if runtime_mode == "geospatial_crab_field":
            return bool(live.get("simulation_paused", True)) or not bool(live.get("physics_armed", False))
        return bool(live.get("simulation_paused", False))

    def _collapse_config(self) -> dict:
        base = dict(self.configs.get("particle_config", {}).get("collapse_behavior", {}))
        live = self.live_control_state if isinstance(self.live_control_state, dict) else {}
        allowed = {
            "behavior_mode", "respawn_on_capture", "minimum_radius", "capture_radius",
            "event_horizon_visual_radius", "core_pressure_strength", "core_pressure_radius",
            "orbital_floor_velocity", "angular_momentum_preservation", "respawn_radius",
        }
        for key in allowed:
            if key in live:
                base[key] = live[key]
        if isinstance(live.get("collapse_behavior"), dict):
            for key in allowed:
                if key in live["collapse_behavior"]:
                    base[key] = live["collapse_behavior"][key]
        return base

    def _count_mask(self, mask) -> int:
        xp = self.compute.xp
        try:
            return int(self.compute.to_float(xp.mean(mask.to(dtype=self.compute.float32_dtype))) * mask.shape[0])
        except Exception:
            try:
                return int(mask.sum().item())
            except Exception:
                return int(mask.sum())

    def _enforce_minimum_radius(self, pos3, radius, minimum_radius: float) -> None:
        xp = self.compute.xp
        if minimum_radius <= 0:
            return
        below = radius < minimum_radius
        if self._count_mask(below) <= 0:
            return
        delta_from_center = pos3 - self.center
        safe_radius = xp.sqrt((delta_from_center * delta_from_center).sum(axis=1) + 1.0e-9)
        outward = delta_from_center / safe_radius[:, None]
        clamped_pos = self.center + outward * minimum_radius
        pos3[...] = xp.where(below[:, None], clamped_pos, pos3)

    def _apply_orbital_floor(self, pos3, vel3, radius, floor_velocity: float, preserve_blend: float) -> None:
        xp = self.compute.xp
        if floor_velocity <= 0 and preserve_blend <= 0:
            return
        radial = pos3 - self.center
        tangent = xp.stack([-radial[:, 2], xp.zeros_like(radial[:, 1]), radial[:, 0]], axis=1)
        tangent_norm = xp.sqrt((tangent * tangent).sum(axis=1) + 1.0e-9)
        tangent = tangent / tangent_norm[:, None]
        vel_mag = xp.sqrt((vel3 * vel3).sum(axis=1) + 1.0e-9)
        need_floor = vel_mag < floor_velocity
        floor_vel = tangent * floor_velocity
        vel3[...] = xp.where(need_floor[:, None], floor_vel, vel3)
        if preserve_blend > 0:
            orbital_component = tangent * xp.clamp(vel_mag, min=floor_velocity, max=10.0)[:, None]
            vel3[...] = (1.0 - preserve_blend) * vel3 + preserve_blend * orbital_component

    def _respawn_captured(self, pos3, vel3, capture_mask, respawn_radius: float) -> None:
        xp = self.compute.xp
        n = pos3.shape[0]
        idx = xp.arange(0, n, dtype=self.compute.float32_dtype)
        angle = idx * 2.399963229728653
        y_wave = xp.sin(idx * 0.013) * 0.35
        x = respawn_radius * xp.cos(angle)
        y = respawn_radius * 0.18 * y_wave
        z = respawn_radius * xp.sin(angle)
        new_pos = xp.stack([x, y, z], axis=1)
        tangent = xp.stack([-xp.sin(angle), xp.zeros_like(y), xp.cos(angle)], axis=1)
        new_vel = tangent * 0.05
        pos3[...] = xp.where(capture_mask[:, None], new_pos, pos3)
        vel3[...] = xp.where(capture_mask[:, None], new_vel, vel3)

    def _place_captured_on_horizon(self, pos3, vel3, capture_mask, horizon_radius: float) -> None:
        xp = self.compute.xp
        delta_from_center = pos3 - self.center
        safe_radius = xp.sqrt((delta_from_center * delta_from_center).sum(axis=1) + 1.0e-9)
        outward = delta_from_center / safe_radius[:, None]
        horizon_pos = self.center + outward * horizon_radius
        pos3[...] = xp.where(capture_mask[:, None], horizon_pos, pos3)
        vel3[...] = xp.where(capture_mask[:, None], vel3 * 0.15, vel3)
