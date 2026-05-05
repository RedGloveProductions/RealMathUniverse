#!/usr/bin/env python3
"""
RealMathUniverse v1.3C
Geospatial particle source loader.

Purpose:
    Load crab navigation CSV rows as actual solver particle positions.
    Longitude -> x, Elevation/Depth -> y, Latitude -> z.

This module intentionally has no dependency on the rest of RMU except numpy/stdlib,
with optional torch conversion handled by geospatial_solver_binding.py.
"""
from __future__ import annotations

import csv
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

DEPTH_ALIASES = [
    "Depth", "depth", "DEPTH",
    "Elevation", "elevation", "ELEVATION",
    "Z", "z", "water_depth", "WaterDepth", "waterDepth",
]
LAT_ALIASES = ["Latitude", "latitude", "LAT", "lat"]
LON_ALIASES = ["Longitude", "longitude", "LON", "lon", "Long", "long"]
DENSITY_ALIASES = ["track_density", "TrackDensity", "density", "Density", "TRACK_DENSITY"]


def _first_existing(columns: Iterable[str], aliases: Iterable[str]) -> Optional[str]:
    column_set = set(columns)
    for name in aliases:
        if name in column_set:
            return name
    lower_map = {c.lower(): c for c in columns}
    for name in aliases:
        found = lower_map.get(name.lower())
        if found:
            return found
    return None


def _safe_float(value, default=np.nan) -> float:
    try:
        if value is None:
            return default
        text = str(value).strip()
        if text == "":
            return default
        return float(text)
    except Exception:
        return default


def _percentile_range(values: np.ndarray, p_low: float = 1.0, p_high: float = 99.0) -> Tuple[float, float]:
    clean = values[np.isfinite(values)]
    if clean.size == 0:
        return 0.0, 1.0
    lo = float(np.percentile(clean, p_low))
    hi = float(np.percentile(clean, p_high))
    if not math.isfinite(lo) or not math.isfinite(hi) or abs(hi - lo) < 1e-12:
        lo = float(np.min(clean))
        hi = float(np.max(clean))
        if abs(hi - lo) < 1e-12:
            hi = lo + 1.0
    return lo, hi


def _remap_clamped(values: np.ndarray, src_lo: float, src_hi: float, dst_lo: float, dst_hi: float) -> np.ndarray:
    denom = src_hi - src_lo
    if abs(denom) < 1e-12:
        return np.full_like(values, (dst_lo + dst_hi) * 0.5, dtype=np.float32)
    t = (values - src_lo) / denom
    t = np.clip(t, 0.0, 1.0)
    return (dst_lo + t * (dst_hi - dst_lo)).astype(np.float32)


def load_geospatial_particles(
    csv_path: str | os.PathLike,
    world_radius: float = 5.75,
    vertical_scale: float = 1.2,
    max_rows: Optional[int] = None,
) -> Dict[str, object]:
    """Load crab CSV into solver-ready arrays.

    Returns dict with:
        positions: float32 [N,4]
        velocities: float32 [N,4]
        forces: float32 [N,4]
        mass: float32 [N]
        density: float32 [N]
        metadata: dict
    """
    path = Path(csv_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Geospatial CSV not found: {path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        lon_col = _first_existing(columns, LON_ALIASES)
        lat_col = _first_existing(columns, LAT_ALIASES)
        depth_col = _first_existing(columns, DEPTH_ALIASES)
        density_col = _first_existing(columns, DENSITY_ALIASES)
        if lon_col is None or lat_col is None or depth_col is None:
            raise ValueError(
                f"CSV must contain longitude, latitude, and depth/elevation columns. "
                f"Found columns: {columns}"
            )

        lon: List[float] = []
        lat: List[float] = []
        dep: List[float] = []
        den: List[float] = []
        for i, row in enumerate(reader):
            if max_rows is not None and i >= max_rows:
                break
            a = _safe_float(row.get(lon_col))
            b = _safe_float(row.get(lat_col))
            c = _safe_float(row.get(depth_col))
            if not (math.isfinite(a) and math.isfinite(b) and math.isfinite(c)):
                continue
            lon.append(a)
            lat.append(b)
            dep.append(c)
            if density_col:
                den.append(_safe_float(row.get(density_col), 1.0))
            else:
                den.append(1.0)

    if not lon:
        raise ValueError(f"No valid geospatial rows found in {path}")

    lon_a = np.asarray(lon, dtype=np.float32)
    lat_a = np.asarray(lat, dtype=np.float32)
    dep_a = np.asarray(dep, dtype=np.float32)
    den_a = np.asarray(den, dtype=np.float32)
    den_a[~np.isfinite(den_a)] = 1.0

    lon_lo, lon_hi = _percentile_range(lon_a)
    lat_lo, lat_hi = _percentile_range(lat_a)
    dep_lo, dep_hi = _percentile_range(dep_a)
    den_lo, den_hi = _percentile_range(den_a)

    x = _remap_clamped(lon_a, lon_lo, lon_hi, -world_radius, world_radius)
    z = _remap_clamped(lat_a, lat_lo, lat_hi, -world_radius, world_radius)
    y = _remap_clamped(dep_a, dep_lo, dep_hi, -vertical_scale, vertical_scale)
    density = _remap_clamped(den_a, den_lo, den_hi, 0.25, 2.0)

    n = int(x.shape[0])
    positions = np.zeros((n, 4), dtype=np.float32)
    positions[:, 0] = x
    positions[:, 1] = y
    positions[:, 2] = z
    positions[:, 3] = 1.0

    velocities = np.zeros((n, 4), dtype=np.float32)
    forces = np.zeros((n, 4), dtype=np.float32)
    mass = density.astype(np.float32)

    metadata = {
        "version": "1.3C",
        "authority": "geospatial_csv",
        "source_csv": str(path),
        "point_count": n,
        "columns": {
            "longitude": lon_col,
            "latitude": lat_col,
            "depth_or_elevation": depth_col,
            "density": density_col,
        },
        "ranges": {
            "longitude": {"p01": lon_lo, "p99": lon_hi, "min": float(np.min(lon_a)), "max": float(np.max(lon_a))},
            "latitude": {"p01": lat_lo, "p99": lat_hi, "min": float(np.min(lat_a)), "max": float(np.max(lat_a))},
            "depth_or_elevation": {"p01": dep_lo, "p99": dep_hi, "min": float(np.min(dep_a)), "max": float(np.max(dep_a))},
            "track_density": {"p01": den_lo, "p99": den_hi, "min": float(np.min(den_a)), "max": float(np.max(den_a))},
        },
        "mapped_bounds": {
            "x": {"min": float(np.min(x)), "max": float(np.max(x))},
            "y": {"min": float(np.min(y)), "max": float(np.max(y))},
            "z": {"min": float(np.min(z)), "max": float(np.max(z))},
        },
        "world_radius": world_radius,
        "vertical_scale": vertical_scale,
        "timestamp_unix": time.time(),
    }
    return {
        "positions": positions,
        "velocities": velocities,
        "forces": forces,
        "mass": mass,
        "density": density,
        "metadata": metadata,
    }


def export_debug_seed(csv_path: str, out_dir: str, world_radius: float = 5.75, vertical_scale: float = 1.2) -> Dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_geospatial_particles(csv_path, world_radius=world_radius, vertical_scale=vertical_scale)
    bin_path = out / "particles_xyz_f32.bin"
    meta_path = out / "metadata.json"
    data["positions"].astype(np.float32).tofile(bin_path)
    meta = dict(data["metadata"])
    meta["binary_out"] = str(bin_path)
    meta["metadata_out"] = str(meta_path)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    return meta
