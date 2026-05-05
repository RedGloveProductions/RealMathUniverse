#!/usr/bin/env python3
"""
RealMathUniverse v1.2A dataset coupling manager.

Reads output/dataset_state.json from v1.1A/v1.1B, converts calibrated dataset
values into safe field-layer drive targets, writes output/dataset_coupling_state.json,
and optionally merges a dataset_coupling block into output/control_state.json.

This does not modify the generic VCV /ch/1-/ch/8 contract.
"""
from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(os.environ.get("RMU_PROJECT_ROOT", "/Users/Joe/Documents/RealMathUniverse"))
CONFIG_PATH = PROJECT_ROOT / "config" / "dataset_coupling_config.json"
DATASET_STATE_PATH = PROJECT_ROOT / "output" / "dataset_state.json"
COUPLING_STATE_PATH = PROJECT_ROOT / "output" / "dataset_coupling_state.json"
CONTROL_STATE_PATH = PROJECT_ROOT / "output" / "control_state.json"


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = f"{os.getpid()}_{time.time_ns()}"
    tmp = path.with_name(f".{path.name}.{stamp}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def map_value(name: str, source: float, cfg: Dict[str, Any]) -> float:
    rule = cfg.get("mapping", {}).get(name, {})
    base = as_float(rule.get("base"), 0.0)
    scale = as_float(rule.get("scale"), 1.0)
    lo = as_float(rule.get("clamp_min"), 0.0)
    hi = as_float(rule.get("clamp_max"), 3.0)
    return clamp(base + source * scale, lo, hi)


def fallback_state(cfg: Dict[str, Any], reason: str) -> Dict[str, Any]:
    fb = cfg.get("fallback", {})
    values = fb.get("values", {})
    targets = fb.get("field_layer_targets", [0.25, 1.0, 0.1, 0.05, 0.2])
    return {
        "version": "1.3E",
        "enabled": bool(cfg.get("enabled", True)),
        "loaded": False,
        "fallback_active": True,
        "fallback_reason": reason,
        "status": "fallback",
        "source": str(DATASET_STATE_PATH),
        "gain": as_float(cfg.get("gain"), 1.0),
        "smooth": as_float(cfg.get("smooth"), 0.15),
        "values": {
            "curvature_drive": as_float(values.get("curvature_drive"), 0.0),
            "temperature_drive": as_float(values.get("temperature_drive"), 0.25),
            "higgs_drive": as_float(values.get("higgs_drive"), 0.35),
            "probability_drive": as_float(values.get("probability_drive"), 0.0),
            "vertical_drive": as_float(values.get("vertical_drive"), 0.0),
        },
        "field_layer_targets": [as_float(x) for x in targets[:5]],
        "summary": f"fallback: {reason}",
        "timestamp_unix": time.time(),
    }


def build_coupling_state(cfg: Dict[str, Any], dataset: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(cfg.get("enabled", True))
    dataset_enabled = bool(dataset.get("enabled", False))
    loaded = bool(dataset.get("loaded", False))
    fallback = bool(dataset.get("fallback_active", True))

    if not enabled:
        return fallback_state(cfg, "dataset coupling disabled in config")
    if not dataset_enabled:
        return fallback_state(cfg, "dataset mode disabled")
    if not loaded or fallback:
        return fallback_state(cfg, dataset.get("fallback_reason", "dataset not loaded"))

    state = dataset.get("state", {}) if isinstance(dataset.get("state", {}), dict) else {}

    curvature = clamp(as_float(state.get("curvature_density"), 0.0), 0.0, 1.0)
    temperature = clamp(as_float(state.get("temperature_proxy"), 0.25), 0.0, 1.0)
    higgs = clamp(as_float(state.get("higgs_lambda"), 0.35), 0.0, 1.0)
    probability = clamp(as_float(state.get("probability_weight"), 0.0), 0.0, 1.0)
    vertical = clamp(abs(as_float(state.get("y"), 0.0)), 0.0, 1.0)

    targets: List[float] = [
        map_value("radial_from_curvature", curvature, cfg),
        map_value("orbital_from_higgs_lambda", higgs, cfg),
        map_value("vertical_from_depth_y", vertical, cfg),
        map_value("turbulence_from_temperature", temperature, cfg),
        map_value("shell_from_probability", probability, cfg),
    ]

    gain = clamp(as_float(cfg.get("gain"), 1.0), 0.0, 3.0)
    smooth = clamp(as_float(cfg.get("smooth"), 0.15), 0.01, 1.0)

    return {
        "version": "1.3E",
        "enabled": True,
        "loaded": True,
        "fallback_active": False,
        "fallback_reason": "none",
        "status": "active",
        "source": str(DATASET_STATE_PATH),
        "source_csv": dataset.get("source_csv", "unknown"),
        "sample_index": dataset.get("sample_index", None),
        "row_count": dataset.get("row_count", None),
        "gain": gain,
        "smooth": smooth,
        "values": {
            "curvature_drive": curvature,
            "temperature_drive": temperature,
            "higgs_drive": higgs,
            "probability_drive": probability,
            "vertical_drive": vertical,
        },
        "field_layer_targets": targets,
        "target_names": ["radial", "orbital", "vertical", "turbulence", "shell"],
        "summary": (
            f"dataset coupling active | C={curvature:.3f} T={temperature:.3f} "
            f"H={higgs:.3f} P={probability:.3f} Y={vertical:.3f}"
        ),
        "timestamp_unix": time.time(),
    }


def merge_control_state(coupling: Dict[str, Any]) -> None:
    control = read_json(CONTROL_STATE_PATH, {})
    if not isinstance(control, dict):
        control = {}
    control["dataset_coupling"] = coupling
    control["updated_by_dataset_coupling_bridge"] = "dataset_coupling_manager_v1_3E"
    control["dataset_coupling_timestamp_unix"] = time.time()
    atomic_write_json(CONTROL_STATE_PATH, control)


def run_once() -> Dict[str, Any]:
    cfg = read_json(CONFIG_PATH, {})
    if not isinstance(cfg, dict):
        cfg = {}
    dataset = read_json(DATASET_STATE_PATH, {})
    if not isinstance(dataset, dict) or not dataset:
        coupling = fallback_state(cfg, "dataset_state.json not readable")
    else:
        coupling = build_coupling_state(cfg, dataset)
    atomic_write_json(COUPLING_STATE_PATH, coupling)
    if bool(cfg.get("write_control_state", True)):
        merge_control_state(coupling)
    return coupling


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.2A dataset coupling bridge")
    parser.add_argument("--once", action="store_true", help="write one coupling state and exit")
    parser.add_argument("--interval", type=float, default=0.20, help="update interval in seconds")
    args = parser.parse_args()

    if args.once:
        state = run_once()
        print(json.dumps(state, indent=2, sort_keys=True))
        return

    print("RealMathUniverse v1.2A dataset coupling bridge running")
    print(f"project_root={PROJECT_ROOT}")
    while True:
        try:
            state = run_once()
            print(state.get("summary", "dataset coupling update"))
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            fallback = fallback_state(read_json(CONFIG_PATH, {}), f"coupling bridge exception: {exc}")
            atomic_write_json(COUPLING_STATE_PATH, fallback)
            print(f"dataset coupling bridge warning: {exc}")
        time.sleep(max(0.05, args.interval))


if __name__ == "__main__":
    main()
