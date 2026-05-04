"""
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
RealMathUniverse Metal Frame Exporter
Version: 0.6A

Purpose:
    Export sampled particle positions and HUD-ready metadata for the Swift/Metal
    renderer.

v0.6A:
    - Adds visual quality metadata.
    - Supports renderer-side sample preset controls through output/control_state.json.
    - Keeps the stable xyz float32 bridge.

Files:
    output/metal_live/particles_xyz_f32.bin
    output/metal_live/metadata.json
$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np


class MetalFrameExporter:
    def __init__(self, project_root: Path, configs, profile, compute, buffer_registry, diagnostics):
        self.project_root = Path(project_root)
        self.configs = configs
        self.profile = profile
        self.compute = compute
        self.buffer_registry = buffer_registry
        self.diagnostics = diagnostics

        render_cfg = configs["render_config"]["render"]
        metal_cfg = render_cfg.get("metal_export", {})

        self.output_dir = self.project_root / metal_cfg.get("output_dir", "output/metal_live")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.binary_path = self.output_dir / metal_cfg.get("binary_filename", "particles_xyz_f32.bin")
        self.metadata_path = self.output_dir / metal_cfg.get("metadata_filename", "metadata.json")
        self.control_state_path = self.project_root / "output" / "control_state.json"

        self.export_every_n_frames = max(1, int(metal_cfg.get("export_every_n_frames", 1)))
        self.default_sample_count = int(render_cfg.get("render_sample_count", 25000))
        self.world_radius = float(render_cfg.get("render_world_radius", 6.0))

        self.frame_index = 0
        self.export_count = 0
        self.export_times_ms: list[float] = []

    def update(self, sim_time: float) -> None:
        self.frame_index += 1
        if self.frame_index % self.export_every_n_frames != 0:
            return

        start = time.perf_counter()
        live_state = self._read_live_control_state()
        sample_count = int(live_state.get("render_sample_count", self.default_sample_count))

        points = self._get_sampled_xyz(sample_count=sample_count)
        self._write_binary(points)
        self._write_metadata(points, sim_time, live_state, sample_count)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.export_times_ms.append(elapsed_ms)
        self.export_count += 1

    def diagnostics_payload(self) -> dict:
        avg = sum(self.export_times_ms) / len(self.export_times_ms) if self.export_times_ms else 0.0
        return {
            "backend": "metal_export",
            "output_dir": str(self.output_dir),
            "binary_path": str(self.binary_path),
            "metadata_path": str(self.metadata_path),
            "control_state_path": str(self.control_state_path),
            "export_count": self.export_count,
            "average_export_ms": avg,
            "max_export_ms": max(self.export_times_ms) if self.export_times_ms else 0.0,
            "default_sample_count": self.default_sample_count,
            "world_radius": self.world_radius,
        }

    def _get_sampled_xyz(self, sample_count: int) -> np.ndarray:
        positions = self.buffer_registry.get("particle_positions")
        n = int(positions.shape[0])
        if n <= 0:
            return np.zeros((0, 3), dtype=np.float32)

        sample_count = max(1000, min(int(sample_count), n))
        stride = max(1, n // max(1, sample_count))
        sampled = positions[0:n:stride, 0:3]

        if hasattr(sampled, "detach"):
            arr = sampled.detach().cpu().numpy()
        elif hasattr(sampled, "get"):
            arr = sampled.get()
        else:
            arr = sampled

        arr = np.asarray(arr, dtype=np.float32)
        if arr.shape[0] > sample_count:
            arr = arr[:sample_count]
        return np.ascontiguousarray(arr[:, 0:3], dtype=np.float32)

    def _write_binary(self, points: np.ndarray) -> None:
        temp_path = self.binary_path.with_suffix(".tmp")
        points.tofile(temp_path)
        temp_path.replace(self.binary_path)

    def _read_live_control_state(self) -> dict:
        if not self.control_state_path.exists():
            return {}
        try:
            with self.control_state_path.open("r", encoding="utf-8") as f:
                state = json.load(f)
            return state if isinstance(state, dict) else {}
        except Exception:
            return {}

    def _write_metadata(self, points: np.ndarray, sim_time: float, live_state: dict, sample_count: int) -> None:
        particle_cfg = self.configs.get("particle_config", {})
        collapse_cfg = dict(particle_cfg.get("collapse_behavior", {}))
        for key, value in live_state.items():
            collapse_cfg[key] = value

        render_cfg = self.configs.get("render_config", {}).get("render", {})
        hud_cfg = render_cfg.get("hud_overlays", {})
        color_cfg = render_cfg.get("color_modes", {})
        camera_cfg = render_cfg.get("camera", {})
        visual_quality_cfg = dict(render_cfg.get("visual_quality", {}))
        for key in (
            "trails_enabled",
            "trail_length",
            "grid_enabled",
            "center_marker_enabled",
            "horizon_ring_enabled",
            "compact_hud_enabled",
            "render_sample_count",
        ):
            if key in live_state:
                visual_quality_cfg[key] = live_state[key]

        metadata = {
            "project": "RealMathUniverse",
            "version": "0.6A",
            "frame_index": self.frame_index,
            "export_count": self.export_count,
            "sim_time": float(sim_time),
            "profile": self.profile.name,
            "compute_backend": self.compute.backend_report.backend_name,
            "point_count": int(points.shape[0]),
            "source_particle_count": int(getattr(self.profile, "particle_count", points.shape[0])),
            "dtype": "float32",
            "layout": "xyz_xyz_xyz",
            "components_per_point": 3,
            "binary_filename": self.binary_path.name,
            "world_radius": self.world_radius,
            "render_sample_count": int(sample_count),
            "behavior_mode": collapse_cfg.get("behavior_mode", "unknown"),
            "minimum_radius": collapse_cfg.get("minimum_radius"),
            "capture_radius": collapse_cfg.get("capture_radius"),
            "event_horizon_visual_radius": collapse_cfg.get("event_horizon_visual_radius"),
            "core_pressure_strength": collapse_cfg.get("core_pressure_strength"),
            "orbital_floor_velocity": collapse_cfg.get("orbital_floor_velocity"),
            "angular_momentum_preservation": collapse_cfg.get("angular_momentum_preservation"),
            "respawn_on_capture": collapse_cfg.get("respawn_on_capture", False),
            "live_control_state": live_state,
            "hud_overlays": hud_cfg,
            "color_modes": color_cfg,
            "camera_defaults": camera_cfg,
            "visual_quality": visual_quality_cfg,
            "timestamp_unix": time.time(),
        }
        temp_path = self.metadata_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        temp_path.replace(self.metadata_path)
