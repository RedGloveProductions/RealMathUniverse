#!/usr/bin/env python3
"""
RealMathUniverse v1.3C
Flexible geospatial solver binding / monkey patch layer.

This is deliberately defensive because RMU has evolved through many patch stages.
It patches particle initializer return objects and common buffer objects so the
solver buffers become the crab CSV particle field instead of the old synthetic
25k cloud.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from src.data.geospatial_particle_source import load_geospatial_particles

PROJECT_ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
DEFAULT_CSV = PROJECT_ROOT / "data/raw/merged_navdata.csv"
AUTHORITY_PATH = PROJECT_ROOT / "output/particle_source_authority.json"
RUNTIME_STATE_PATH = PROJECT_ROOT / "output/runtime_state.json"
BEHAVIOR_STATE_PATH = PROJECT_ROOT / "output/behavior_state.json"


def _get_from_config(config: Any, *keys, default=None):
    cur = config
    try:
        for k in keys:
            if isinstance(cur, dict):
                cur = cur[k]
            else:
                cur = getattr(cur, k)
        return cur
    except Exception:
        return default


def is_geospatial_requested(config: Any = None) -> bool:
    mode = _get_from_config(config, "particles", "initialization_mode", default=None)
    if mode is None:
        mode = _get_from_config(config, "particle_config", "particles", "initialization_mode", default=None)
    if mode is None:
        # If config is the whole loaded config bundle, try common nesting.
        mode = _get_from_config(config, "particle_config", "particles", "initialization_mode", default=None)
    if mode == "geospatial_crab_field":
        return True
    try:
        pc = PROJECT_ROOT / "config/particle_config.json"
        if pc.exists():
            with pc.open("r", encoding="utf-8") as f:
                j = json.load(f)
            return j.get("particles", {}).get("initialization_mode") == "geospatial_crab_field"
    except Exception:
        pass
    return False


def get_csv_path(config: Any = None) -> Path:
    candidate = _get_from_config(config, "particles", "geospatial_source_csv", default=None)
    if not candidate:
        candidate = _get_from_config(config, "particle_config", "particles", "geospatial_source_csv", default=None)
    if not candidate:
        try:
            pc = PROJECT_ROOT / "config/particle_config.json"
            if pc.exists():
                with pc.open("r", encoding="utf-8") as f:
                    j = json.load(f)
                candidate = j.get("particles", {}).get("geospatial_source_csv")
        except Exception:
            candidate = None
    return Path(candidate or DEFAULT_CSV).expanduser()


def _to_like(existing: Any, arr: np.ndarray):
    if existing is None:
        return arr
    mod = type(existing).__module__
    if "torch" in mod:
        import torch
        return torch.as_tensor(arr, dtype=getattr(existing, "dtype", torch.float32), device=getattr(existing, "device", None))
    if isinstance(existing, np.ndarray):
        return arr.astype(existing.dtype if existing.dtype else np.float32)
    # Last resort: return numpy array.
    return arr


def _set_attr_or_key(obj: Any, names, value_np: np.ndarray) -> bool:
    # dict path
    if isinstance(obj, dict):
        for name in names:
            if name in obj:
                obj[name] = _to_like(obj.get(name), value_np)
                return True
        obj[names[0]] = value_np
        return True
    # object attr path
    for name in names:
        if hasattr(obj, name):
            current = getattr(obj, name)
            try:
                setattr(obj, name, _to_like(current, value_np))
                return True
            except Exception:
                pass
    try:
        setattr(obj, names[0], value_np)
        return True
    except Exception:
        return False


def apply_geospatial_to_buffers(buffer_obj: Any, config: Any = None, source: str = "unknown") -> Any:
    if not is_geospatial_requested(config):
        return buffer_obj
    csv_path = get_csv_path(config)
    geo = load_geospatial_particles(csv_path)
    pos = geo["positions"]
    vel = geo["velocities"]
    frc = geo["forces"]
    mass = geo["mass"]
    n = int(pos.shape[0])

    _set_attr_or_key(buffer_obj, ["particle_positions", "positions", "pos"], pos)
    _set_attr_or_key(buffer_obj, ["particle_velocities", "velocities", "vel"], vel)
    _set_attr_or_key(buffer_obj, ["particle_forces", "forces", "force"], frc)
    _set_attr_or_key(buffer_obj, ["particle_mass", "mass", "masses"], mass)

    # Species: keep existing if present, but resize to N with zeros if possible.
    species = np.zeros((n,), dtype=np.int32)
    _set_attr_or_key(buffer_obj, ["particle_species", "species"], species)

    meta = dict(geo["metadata"])
    meta.update({
        "status": "bound_to_solver_buffers",
        "source": source,
        "expected_particle_count": n,
        "authority": "geospatial_csv",
        "live_output_should_be_python_solver": True,
        "timestamp_unix": time.time(),
    })
    AUTHORITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUTHORITY_PATH.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)

    # Reset unsafe runtime latches so geospatial starts stable/paused.
    safe_runtime = {
        "version": "1.3C",
        "runtime_mode": "geospatial_crab_field",
        "geospatial_enabled": True,
        "simulation_paused": True,
        "physics_armed": False,
        "particle_source_authority": "geospatial_csv",
        "particle_count": n,
        "behavior_mode": "stable_orbit_cloud",
        "behavior_lock": False,
        "respawn_on_capture": False,
        "updated_by": "geospatial_solver_binding_v1_3C",
        "timestamp_unix": time.time(),
    }
    try:
        with RUNTIME_STATE_PATH.open("w", encoding="utf-8") as f:
            json.dump(safe_runtime, f, indent=2, sort_keys=True)
    except Exception:
        pass
    try:
        with BEHAVIOR_STATE_PATH.open("w", encoding="utf-8") as f:
            json.dump({
                "version": "1.3C",
                "behavior_mode": "stable_orbit_cloud",
                "behavior_lock": False,
                "behavior_source": "geospatial_solver_binding_reset",
                "collapse_behavior": {
                    "behavior_mode": "stable_orbit_cloud",
                    "locked": False,
                    "source": "geospatial_solver_binding_reset",
                    "timestamp_unix": time.time(),
                },
                "updated_by": "geospatial_solver_binding_v1_3C",
                "timestamp_unix": time.time(),
            }, f, indent=2, sort_keys=True)
    except Exception:
        pass
    return buffer_obj


def _wrap_method(cls, method_name: str):
    if not hasattr(cls, method_name):
        return False
    original = getattr(cls, method_name)
    if getattr(original, "_rmu_geospatial_wrapped", False):
        return False

    def wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        config = None
        for obj in (getattr(self, "config", None), getattr(self, "particle_config", None)) + args:
            if obj is not None:
                config = obj
                break
        if result is not None:
            try:
                result = apply_geospatial_to_buffers(result, config=config, source=f"{cls.__name__}.{method_name}:return")
            except Exception as e:
                print(f"RMU v1.3C geospatial binding warning on return: {e}")
        for attr in ("buffers", "particle_buffers", "state", "buffer_registry"):
            if hasattr(self, attr):
                try:
                    patched = apply_geospatial_to_buffers(getattr(self, attr), config=config, source=f"{cls.__name__}.{method_name}:{attr}")
                    setattr(self, attr, patched)
                except Exception:
                    pass
        return result
    wrapped._rmu_geospatial_wrapped = True
    setattr(cls, method_name, wrapped)
    return True


def install_geospatial_particle_initializer_patch(module_globals: Optional[Dict[str, Any]] = None) -> None:
    module_globals = module_globals or {}
    method_names = [
        "initialize", "initialize_particles", "create_particles", "create_initial_state",
        "build_particle_buffers", "create_particle_buffers", "init_buffers", "build_buffers",
        "initialize_buffers", "reset", "reset_particles",
    ]
    patched = []
    for name, obj in list(module_globals.items()):
        if isinstance(obj, type):
            lname = name.lower()
            if "particle" in lname or "initializer" in lname or "buffer" in lname:
                for m in method_names:
                    if _wrap_method(obj, m):
                        patched.append(f"{name}.{m}")
    if patched:
        print("RMU v1.3C geospatial solver binding installed:", ", ".join(patched))
    else:
        print("RMU v1.3C geospatial solver binding loaded; no initializer methods patched yet.")
