#!/usr/bin/env python3
"""
RealMathUniverse v1.3D22
Geospatial Crab Particle Field Loader

Purpose:
    Turn merged_navdata.csv into the renderer's live particle field.

Contract:
    Longitude -> x
    Latitude  -> z
    Elevation/Depth -> y
    track_density -> intensity metadata and future mass/curvature driver

The Metal renderer currently reads output/metal_live/particles_xyz_f32.bin
as tightly packed float32 triples: x, y, z.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT_DEFAULT = Path("/Users/Joe/Documents/RealMathUniverse")
SOURCE_DEFAULT = PROJECT_ROOT_DEFAULT / "data" / "raw" / "merged_navdata.csv"
RUNTIME_STATE = PROJECT_ROOT_DEFAULT / "output" / "runtime_state.json"
STATE_OUT = PROJECT_ROOT_DEFAULT / "output" / "geospatial_particle_state.json"
LIVE_DIR = PROJECT_ROOT_DEFAULT / "output" / "metal_live"
BINARY_OUT = LIVE_DIR / "particles_xyz_f32.bin"
METADATA_OUT = LIVE_DIR / "metadata.json"

DEPTH_ALIASES = ["Depth", "depth", "DEPTH", "Elevation", "elevation", "ELEVATION", "Z", "z", "water_depth", "WaterDepth"]
LAT_ALIASES = ["Latitude", "latitude", "LAT", "lat"]
LON_ALIASES = ["Longitude", "longitude", "LON", "lon", "Long", "long"]
DENSITY_ALIASES = ["track_density", "density", "TrackDensity", "TRACK_DENSITY"]


def _atomic_write_json(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
    tmp.replace(path)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _read_json(path: Path) -> Dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _first_column(columns: Iterable[str], aliases: List[str]) -> Optional[str]:
    cols = list(columns)
    lower_map = {c.lower(): c for c in cols}
    for a in aliases:
        if a in cols:
            return a
        if a.lower() in lower_map:
            return lower_map[a.lower()]
    return None


def _safe_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        s = str(value).strip()
        if not s:
            return None
        f = float(s)
        if not math.isfinite(f):
            return None
        return f
    except Exception:
        return None


def _percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    w = pos - lo
    return sorted_values[lo] * (1.0 - w) + sorted_values[hi] * w


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _map_linear(value: float, src_min: float, src_max: float, dst_min: float, dst_max: float) -> float:
    if abs(src_max - src_min) < 1e-12:
        return (dst_min + dst_max) * 0.5
    t = (value - src_min) / (src_max - src_min)
    t = _clamp(t, 0.0, 1.0)
    return dst_min + t * (dst_max - dst_min)


@dataclass
class GeospatialBuild:
    positions: List[Tuple[float, float, float]]
    stats: Dict
    metadata: Dict


def build_geospatial_field(
    source_csv: Path = SOURCE_DEFAULT,
    world_radius: float = 5.75,
    vertical_scale: float = 1.20,
    max_points: Optional[int] = None,
) -> GeospatialBuild:
    if not source_csv.exists():
        raise FileNotFoundError(f"source CSV not found: {source_csv}")

    with source_csv.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        lon_col = _first_column(columns, LON_ALIASES)
        lat_col = _first_column(columns, LAT_ALIASES)
        depth_col = _first_column(columns, DEPTH_ALIASES)
        density_col = _first_column(columns, DENSITY_ALIASES)

        if not lon_col or not lat_col:
            raise ValueError(f"CSV requires longitude and latitude columns. Found columns: {columns}")

        raw: List[Tuple[float, float, float, float]] = []
        for row in reader:
            lon = _safe_float(row.get(lon_col))
            lat = _safe_float(row.get(lat_col))
            dep = _safe_float(row.get(depth_col)) if depth_col else 0.0
            den = _safe_float(row.get(density_col)) if density_col else 1.0
            if lon is None or lat is None:
                continue
            if dep is None:
                dep = 0.0
            if den is None:
                den = 1.0
            raw.append((lon, lat, dep, den))
            if max_points is not None and len(raw) >= max_points:
                break

    if not raw:
        raise ValueError("No valid geospatial rows loaded.")

    lons = sorted(r[0] for r in raw)
    lats = sorted(r[1] for r in raw)
    deps = sorted(r[2] for r in raw)
    dens = sorted(r[3] for r in raw)

    lon_lo, lon_hi = _percentile(lons, 0.01), _percentile(lons, 0.99)
    lat_lo, lat_hi = _percentile(lats, 0.01), _percentile(lats, 0.99)
    dep_lo, dep_hi = _percentile(deps, 0.01), _percentile(deps, 0.99)
    den_lo, den_hi = _percentile(dens, 0.01), _percentile(dens, 0.99)

    positions: List[Tuple[float, float, float]] = []
    for lon, lat, dep, den in raw:
        x = _map_linear(lon, lon_lo, lon_hi, -world_radius, world_radius)
        z = _map_linear(lat, lat_lo, lat_hi, -world_radius, world_radius)
        # Depth/elevation values are negative. Preserve their sign relationship while keeping a compact vertical field.
        y = _map_linear(dep, dep_lo, dep_hi, -vertical_scale, vertical_scale)
        positions.append((x, y, z))

    stats = {
        "columns": {
            "longitude": lon_col,
            "latitude": lat_col,
            "depth_or_elevation": depth_col,
            "density": density_col,
        },
        "row_count": len(raw),
        "point_count": len(positions),
        "source_csv": str(source_csv),
        "ranges": {
            "longitude": {"p01": lon_lo, "p99": lon_hi, "min": lons[0], "max": lons[-1]},
            "latitude": {"p01": lat_lo, "p99": lat_hi, "min": lats[0], "max": lats[-1]},
            "depth_or_elevation": {"p01": dep_lo, "p99": dep_hi, "min": deps[0], "max": deps[-1]},
            "track_density": {"p01": den_lo, "p99": den_hi, "min": dens[0], "max": dens[-1]},
        },
        "mapped_bounds": {
            "x": {"min": min(p[0] for p in positions), "max": max(p[0] for p in positions)},
            "y": {"min": min(p[1] for p in positions), "max": max(p[1] for p in positions)},
            "z": {"min": min(p[2] for p in positions), "max": max(p[2] for p in positions)},
        },
        "world_radius": world_radius,
        "vertical_scale": vertical_scale,
    }

    metadata = {
        "version": "1.3D22",
        "profile": "geospatial_crab_field",
        "compute_backend": "csv_geospatial_loader",
        "behavior_mode": "geospatial_static_paused",
        "source_particle_count": len(positions),
        "render_sample_count": len(positions),
        "world_radius": world_radius,
        "frame_index": 0,
        "export_count": len(positions),
        "sim_time": 0.0,
        "minimum_radius": 0.24,
        "capture_radius": 0.075,
        "event_horizon_visual_radius": 0.34,
        "respawn_on_capture": False,
        "timestamp_unix": time.time(),
        "geospatial_particle_field": stats,
        "visual_quality": {
            "trails_enabled": False,
            "grid_enabled": True,
            "center_marker_enabled": True,
            "horizon_ring_enabled": False,
        },
    }
    return GeospatialBuild(positions=positions, stats=stats, metadata=metadata)


def export_geospatial_field(source_csv: Path = SOURCE_DEFAULT, state_reason: str = "manual_export") -> Dict:
    build = build_geospatial_field(source_csv=source_csv)
    flat = bytearray()
    for x, y, z in build.positions:
        flat.extend(struct.pack("fff", float(x), float(y), float(z)))
    _atomic_write_bytes(BINARY_OUT, bytes(flat))
    _atomic_write_json(METADATA_OUT, build.metadata)

    state = {
        "version": "1.3D22",
        "status": "exported",
        "reason": state_reason,
        "timestamp_unix": time.time(),
        "binary_out": str(BINARY_OUT),
        "metadata_out": str(METADATA_OUT),
        **build.stats,
    }
    _atomic_write_json(STATE_OUT, state)
    return state


def ensure_runtime_state() -> Dict:
    runtime = _read_json(RUNTIME_STATE)
    changed = False
    if not runtime:
        runtime = {}
        changed = True
    defaults = {
        "version": "1.3D22",
        "updated_by": "geospatial_particle_field_v1_3A",
        "runtime_mode": "geospatial_crab_field",
        "geospatial_enabled": True,
        "simulation_paused": True,
        "physics_armed": False,
        "spacebar_mode": "run_pause_geospatial",
        "particle_source_mode": "crab_nav_csv_particles",
        "particle_source_csv": str(SOURCE_DEFAULT),
        "behavior_mode": "stable_orbit_cloud",
        "respawn_on_capture": False,
        "timestamp_unix": time.time(),
    }
    for k, v in defaults.items():
        if k not in runtime:
            runtime[k] = v
            changed = True
    if changed:
        _atomic_write_json(RUNTIME_STATE, runtime)
    return runtime


def watch(interval: float = 0.50, source_csv: Path = SOURCE_DEFAULT) -> None:
    last_export = 0.0
    while True:
        runtime = ensure_runtime_state()
        enabled = bool(runtime.get("geospatial_enabled", True))
        paused = bool(runtime.get("simulation_paused", True))
        mode = str(runtime.get("runtime_mode", "geospatial_crab_field"))
        if enabled and paused and mode == "geospatial_crab_field":
            now = time.time()
            # Export repeatedly while paused so the geospatial field remains the renderer source
            # even if another exporter is also running.
            if now - last_export >= interval:
                try:
                    export_geospatial_field(source_csv=source_csv, state_reason="paused_geospatial_hold")
                except Exception as exc:
                    _atomic_write_json(STATE_OUT, {
                        "version": "1.3D22",
                        "status": "error",
                        "error": str(exc),
                        "timestamp_unix": time.time(),
                    })
                last_export = now
        time.sleep(interval)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(SOURCE_DEFAULT))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--interval", type=float, default=0.50)
    args = ap.parse_args()

    source = Path(args.source)
    if args.status:
        state = _read_json(STATE_OUT)
        runtime = _read_json(RUNTIME_STATE)
        print(json.dumps({"geospatial_particle_state": state, "runtime_state": runtime}, indent=2, sort_keys=True))
        return
    if args.once:
        print(json.dumps(export_geospatial_field(source_csv=source, state_reason="once"), indent=2, sort_keys=True))
        return
    if args.watch:
        watch(interval=args.interval, source_csv=source)
        return
    print(json.dumps(export_geospatial_field(source_csv=source, state_reason="default_once"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
