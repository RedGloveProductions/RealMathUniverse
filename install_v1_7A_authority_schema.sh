#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Authority Schema Foundation Installer
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Project:
#   RealMathUniverse
#
# Patch:
#   v1.7A Authority Schema Foundation
#
# Purpose:
#   Add a formal runtime authority resolver that reads the existing source state
#   files and produces one canonical output/effective_state.json file.
#
# What this patch does:
#   1. Adds config/authority_schema.json
#   2. Adds src/runtime/authority_resolver.py
#   3. Adds scripts/run_authority_resolver.sh
#   4. Adds scripts/run_metal_session_authority.sh
#   5. Adds scripts/monitor_effective_state.sh
#   6. Creates output/effective_state.json at runtime
#
# What this patch does NOT do:
#   1. It does not delete old state files.
#   2. It does not rewrite the Swift renderer.
#   3. It does not force the HUD to use effective_state.json yet.
#   4. It does not alter the existing VCV bridge.
#
# Design rule:
#   Source files report raw truth.
#   The resolver chooses effective runtime truth.
#   The HUD and future renderer authority patches should read effective truth.
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"

echo "============================================================"
echo "RealMathUniverse v1.7A Authority Schema Foundation Installer"
echo "Project root: ${PROJECT_ROOT}"
echo "============================================================"

if [[ ! -d "${PROJECT_ROOT}" ]]; then
  echo "ERROR: Project root not found: ${PROJECT_ROOT}"
  echo "Set PROJECT_ROOT manually if needed:"
  echo "  PROJECT_ROOT=/path/to/RealMathUniverse ./install_v1_7A_authority_schema.sh"
  exit 1
fi

cd "${PROJECT_ROOT}"

mkdir -p config
mkdir -p src/runtime
mkdir -p scripts
mkdir -p output
mkdir -p output/logs
mkdir -p output/backups/v1_7A_authority_schema

STAMP="$(date +"%Y%m%d_%H%M%S")"

backup_if_exists() {
  local file_path="$1"
  if [[ -f "${file_path}" ]]; then
    local safe_name
    safe_name="$(echo "${file_path}" | sed 's#/#__#g')"
    cp "${file_path}" "output/backups/v1_7A_authority_schema/${safe_name}.${STAMP}.bak"
    echo "Backed up ${file_path}"
  fi
}

backup_if_exists "config/authority_schema.json"
backup_if_exists "src/runtime/authority_resolver.py"
backup_if_exists "scripts/run_authority_resolver.sh"
backup_if_exists "scripts/run_metal_session_authority.sh"
backup_if_exists "scripts/monitor_effective_state.sh"

cat > config/authority_schema.json <<'JSON'
{
  "schema": "rmu.authority_schema.v1",
  "version": "1.7A-authority-schema-foundation",
  "description": "Formal authority schema for RealMathUniverse runtime resolution. Source files report raw truth. The resolver publishes effective truth.",
  "project_rules": {
    "one_layer_owns_each_decision": true,
    "source_files_are_not_final_authority": true,
    "hud_is_display_only": true,
    "metal_consumes_effective_values": true,
    "control_state_is_compatibility_snapshot": true
  },
  "files": {
    "runtime_state": {
      "path": "output/runtime_state.json",
      "role": "runtime lifecycle and command authority",
      "authority_level": 2
    },
    "vcv_state": {
      "path": "output/vcv_state.json",
      "role": "VCV source signal truth",
      "authority_level": 1
    },
    "dataset_state": {
      "path": "output/dataset_state.json",
      "role": "dataset source/load truth",
      "authority_level": 1
    },
    "dataset_coupling_state": {
      "path": "output/dataset_coupling_state.json",
      "role": "dataset-derived coupling proposal truth",
      "authority_level": 1
    },
    "behavior_state": {
      "path": "output/behavior_state.json",
      "role": "manual behavior latch and compatibility behavior memory",
      "authority_level": 1
    },
    "control_state": {
      "path": "output/control_state.json",
      "role": "legacy composite compatibility report, not final authority",
      "authority_level": 5
    },
    "effective_state": {
      "path": "output/effective_state.json",
      "role": "canonical resolved runtime truth",
      "authority_level": 5
    }
  },
  "domains": {
    "runtime_lifecycle": {
      "default_authority": "renderer_runtime",
      "fallback": "safe_paused"
    },
    "dataset_source": {
      "default_authority": "dataset_loader",
      "fallback": "synthetic_or_last_valid"
    },
    "particle_positions": {
      "default_authority": "metal_gpu_live_buffer",
      "fallback": "crab_nav_csv_seed"
    },
    "species_identity": {
      "default_authority": "species_identity_sidecar",
      "fallback": "crab_default"
    },
    "behavior": {
      "default_authority": "manual",
      "external_authority": "vcv",
      "vcv_code_channel": "/ch/18",
      "vcv_gate_channel": "/ch/19",
      "vcv_gate_threshold_volts": 5.0,
      "fallback": "manual"
    },
    "field_recipe": {
      "default_authority": "manual_or_internal",
      "external_authority": "vcv",
      "vcv_scene_channel": "/ch/8",
      "fallback": "last_valid_or_default"
    },
    "gravity": {
      "default_authority": "internal",
      "external_authority": "vcv",
      "vcv_position_channel": "/ch/14",
      "vcv_strength_channel": "/ch/15",
      "fallback": "internal"
    },
    "species_mass": {
      "default_authority": "species_defaults",
      "external_authority": "vcv_poly_bank",
      "bank_a_channel": "/ch/10",
      "bank_b_channel": "/ch/11",
      "species_count": 22,
      "bank_a_count": 16,
      "bank_b_count": 6,
      "fallback": "species_defaults"
    },
    "camera": {
      "default_authority": "keyboard_mouse",
      "fallback": "preset_camera"
    },
    "capture": {
      "default_authority": "renderer",
      "fallback": "disabled"
    }
  },
  "behavior_codes": {
    "0": "none",
    "1": "stable_orbit",
    "2": "radial_field",
    "3": "orbital_field",
    "4": "turbulence_field",
    "5": "black_hole_capture",
    "6": "shell_boundary",
    "7": "species_controlled"
  },
  "field_recipes": {
    "0": {
      "name": "manual_or_default",
      "weights": [1.0, 1.0, 1.0, 1.0, 1.0]
    },
    "1": {
      "name": "radial_focus",
      "weights": [2.5, 0.25, 0.25, 0.25, 0.5]
    },
    "2": {
      "name": "orbital_focus",
      "weights": [0.25, 2.5, 0.25, 0.5, 0.5]
    },
    "3": {
      "name": "vertical_focus",
      "weights": [0.25, 0.25, 2.5, 0.5, 0.5]
    },
    "4": {
      "name": "turbulence_focus",
      "weights": [0.5, 0.75, 0.25, 2.5, 0.75]
    },
    "5": {
      "name": "shell_focus",
      "weights": [0.5, 0.75, 0.25, 0.75, 2.5]
    },
    "6": {
      "name": "full_hybrid",
      "weights": [1.5, 1.5, 1.0, 1.25, 1.25]
    },
    "7": {
      "name": "species_driven",
      "weights": [1.0, 1.0, 0.5, 1.75, 1.25]
    }
  }
}
JSON

cat > src/runtime/authority_resolver.py <<'PY'
#!/usr/bin/env python3
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Authority Resolver
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Project:
#   RealMathUniverse
#
# File:
#   src/runtime/authority_resolver.py
#
# Patch:
#   v1.7A Authority Schema Foundation
#
# Purpose:
#   Read existing RMU source state files and publish a canonical
#   output/effective_state.json file.
#
# Philosophy:
#   Source files report raw truth.
#   The resolver chooses effective truth.
#   The HUD should display effective truth.
#   The renderer should eventually consume effective truth before Metal encode.
#
# Existing source files:
#   output/runtime_state.json
#   output/vcv_state.json
#   output/dataset_state.json
#   output/dataset_coupling_state.json
#   output/behavior_state.json
#   output/control_state.json
#
# New canonical output:
#   output/effective_state.json
#
# 3P's:
#   Purpose:
#     Build one reliable authority snapshot from scattered runtime files.
#
#   Parameters:
#     --root            Project root.
#     --once            Run once and exit.
#     --interval        Loop interval in seconds.
#     --stale-ms        Freshness threshold in milliseconds.
#     --quiet           Reduce console output.
#
#   Product:
#     Atomic output/effective_state.json plus resolver log entries.
#
# Test plan:
#   1. Run once:
#        python3 src/runtime/authority_resolver.py --root . --once
#
#   2. Inspect output:
#        cat output/effective_state.json | python3 -m json.tool
#
#   3. Run live:
#        ./scripts/run_authority_resolver.sh
#
#   4. Monitor:
#        ./scripts/monitor_effective_state.sh
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "rmu.effective_state.v1"
PATCH_VERSION = "1.7A-authority-schema-foundation"


# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def round_float(value: Any, digits: int = 6) -> float:
    return round(safe_float(value), digits)


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd = -1
    tmp_path: Optional[Path] = None

    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            text=True,
        )
        tmp_path = Path(tmp_name)

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(str(tmp_path), str(path))

    finally:
        if fd != -1:
            try:
                os.close(fd)
            except OSError:
                pass

        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def read_json_file(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    meta = {
        "path": str(path),
        "exists": path.exists(),
        "loaded": False,
        "error": None,
        "mtime": None,
        "age_ms": None,
        "size_bytes": 0,
    }

    if not path.exists():
        return {}, meta

    try:
        stat = path.stat()
        meta["mtime"] = stat.st_mtime
        meta["size_bytes"] = stat.st_size
        meta["age_ms"] = max(0, int((time.time() - stat.st_mtime) * 1000))

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        if isinstance(data, dict):
            meta["loaded"] = True
            return data, meta

        meta["error"] = f"JSON root was {type(data).__name__}, expected object"
        return {}, meta

    except Exception as exc:
        meta["error"] = f"{type(exc).__name__}: {exc}"
        return {}, meta


def deep_get(data: Dict[str, Any], paths: List[List[str]], default: Any = None) -> Any:
    for path in paths:
        cur: Any = data
        ok = True

        for key in path:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break

        if ok:
            return cur

    return default


def normalize_channel_key(channel: Any) -> Optional[str]:
    if channel is None:
        return None

    text = str(channel).strip()
    if not text:
        return None

    if text.startswith("/ch/"):
        return text

    if text.startswith("ch/"):
        return "/" + text

    if text.startswith("ch"):
        suffix = text[2:].strip("/")
        if suffix.isdigit():
            return f"/ch/{int(suffix)}"

    if text.isdigit():
        return f"/ch/{int(text)}"

    return text


def extract_channels(vcv_state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Accepts multiple bridge schemas:
      channels: {"/ch/1": {...}}
      raw_channels: {"/ch/1": ...}
      direct_channels: {"/ch/1": {...}}
      mapped_values: {"behavior_code": ...}
      values: {"/ch/1": ...}
    Returns normalized /ch/N dict entries.
    """

    result: Dict[str, Dict[str, Any]] = {}

    candidates = [
        vcv_state.get("channels"),
        vcv_state.get("raw_channels"),
        vcv_state.get("direct_channels"),
        vcv_state.get("values"),
        deep_get(vcv_state, [["vcv", "channels"]], None),
        deep_get(vcv_state, [["state", "channels"]], None),
    ]

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        for raw_key, raw_value in candidate.items():
            key = normalize_channel_key(raw_key)
            if key is None:
                continue

            entry = result.setdefault(key, {})
            if isinstance(raw_value, dict):
                entry.update(raw_value)
            else:
                entry["raw"] = raw_value
                entry["value"] = raw_value

    # Compatibility with flat channel names like ch18, channel_18, etc.
    for raw_key, raw_value in vcv_state.items():
        if not isinstance(raw_key, str):
            continue

        key = None

        if raw_key.startswith("/ch/"):
            key = normalize_channel_key(raw_key)
        elif raw_key.startswith("ch") and raw_key[2:].isdigit():
            key = normalize_channel_key(raw_key)
        elif raw_key.startswith("channel_") and raw_key.replace("channel_", "").isdigit():
            key = normalize_channel_key(raw_key.replace("channel_", ""))

        if key:
            entry = result.setdefault(key, {})
            if isinstance(raw_value, dict):
                entry.update(raw_value)
            else:
                entry["raw"] = raw_value
                entry["value"] = raw_value

    labels = vcv_state.get("labels")
    if isinstance(labels, dict):
        for raw_key, label in labels.items():
            key = normalize_channel_key(raw_key)
            if key:
                result.setdefault(key, {})["label"] = label

    mapped_values = vcv_state.get("mapped_values")
    if isinstance(mapped_values, dict):
        for label, value in mapped_values.items():
            if label == "behavior_code":
                result.setdefault("/ch/18", {})["mapped"] = value
                result.setdefault("/ch/18", {})["label"] = "behavior_code"
            elif label == "behavior_authority_gate":
                result.setdefault("/ch/19", {})["mapped"] = value
                result.setdefault("/ch/19", {})["label"] = "behavior_authority_gate"
            elif label == "scene_index":
                result.setdefault("/ch/8", {})["mapped"] = value
                result.setdefault("/ch/8", {})["label"] = "scene_index"
            elif label == "gravity_well_strength":
                result.setdefault("/ch/15", {})["mapped"] = value
                result.setdefault("/ch/15", {})["label"] = "gravity_well_strength"

    # Direct top-level compatibility keys.
    direct_label_map = {
        "behavior_code": "/ch/18",
        "behavior_authority_gate": "/ch/19",
        "scene_index": "/ch/8",
        "gravity_well_strength": "/ch/15",
    }

    for label, channel in direct_label_map.items():
        if label in vcv_state:
            result.setdefault(channel, {})["mapped"] = vcv_state[label]
            result.setdefault(channel, {})["label"] = label

    return result


def channel_scalar(
    channels: Dict[str, Dict[str, Any]],
    channel: str,
    default: float = 0.0,
    prefer_mapped: bool = True,
) -> float:
    entry = channels.get(channel, {})
    if not isinstance(entry, dict):
        return default

    key_order = ["mapped", "value", "smoothed", "raw"] if prefer_mapped else ["raw", "value", "mapped", "smoothed"]

    for key in key_order:
        if key in entry:
            value = entry.get(key)
            if isinstance(value, list) and value:
                return safe_float(value[0], default)
            return safe_float(value, default)

    voices = entry.get("voices")
    if isinstance(voices, list) and voices:
        return safe_float(voices[0], default)

    return default


def channel_voices(
    channels: Dict[str, Dict[str, Any]],
    channel: str,
    max_count: Optional[int] = None,
) -> List[float]:
    entry = channels.get(channel, {})
    if not isinstance(entry, dict):
        return []

    for key in ["voices", "poly", "values", "raw_values", "mapped_values"]:
        value = entry.get(key)
        if isinstance(value, list):
            floats = [safe_float(v, 0.0) for v in value]
            return floats[:max_count] if max_count is not None else floats

    value = None
    for key in ["mapped", "value", "smoothed", "raw"]:
        if key in entry:
            value = entry.get(key)
            break

    if isinstance(value, list):
        floats = [safe_float(v, 0.0) for v in value]
        return floats[:max_count] if max_count is not None else floats

    if value is not None:
        return [safe_float(value, 0.0)]

    return []


def detect_vcv_fresh(vcv_data: Dict[str, Any], meta: Dict[str, Any], stale_ms: int) -> bool:
    direct_status = deep_get(
        vcv_data,
        [
            ["fresh"],
            ["active"],
            ["vcv", "fresh"],
            ["vcv", "active"],
            ["status", "fresh"],
            ["status", "active"],
        ],
        None,
    )

    if isinstance(direct_status, bool):
        if not direct_status:
            return False

    age_ms = safe_int(meta.get("age_ms"), stale_ms + 1)
    if age_ms > stale_ms:
        return False

    status_text = str(
        deep_get(
            vcv_data,
            [
                ["status"],
                ["vcv_status"],
                ["state"],
                ["vcv", "status"],
            ],
            "",
        )
    ).lower()

    if status_text in {"stale", "off", "offline", "inactive", "dead"}:
        return False

    return meta.get("loaded", False)


def remap_bipolar_to_range(raw: float, out_min: float, out_max: float) -> float:
    """
    Maps a common -5V to +5V signal into a target range.
    If the value already looks normalized or mapped, this function is only used
    where no mapped value exists.
    """
    normalized = clamp((raw + 5.0) / 10.0, 0.0, 1.0)
    return out_min + normalized * (out_max - out_min)


def behavior_name(code: int, schema: Dict[str, Any]) -> str:
    table = schema.get("behavior_codes")
    if isinstance(table, dict):
        return str(table.get(str(code), f"behavior_{code}"))

    fallback = {
        0: "none",
        1: "stable_orbit",
        2: "radial_field",
        3: "orbital_field",
        4: "turbulence_field",
        5: "black_hole_capture",
        6: "shell_boundary",
        7: "species_controlled",
    }
    return fallback.get(code, f"behavior_{code}")


def field_recipe_for_scene(scene_index: int, schema: Dict[str, Any]) -> Dict[str, Any]:
    recipes = schema.get("field_recipes")
    if isinstance(recipes, dict):
        recipe = recipes.get(str(scene_index))
        if isinstance(recipe, dict):
            return {
                "scene_index": scene_index,
                "recipe_name": str(recipe.get("name", f"scene_{scene_index}")),
                "weights": normalize_field_weights(recipe.get("weights")),
            }

    return {
        "scene_index": scene_index,
        "recipe_name": "manual_or_default",
        "weights": normalize_field_weights([1.0, 1.0, 1.0, 1.0, 1.0]),
    }


def normalize_field_weights(value: Any) -> Dict[str, float]:
    names = ["radial", "orbital", "vertical", "turbulence", "shell"]

    if isinstance(value, dict):
        return {
            "radial": round_float(value.get("radial", 1.0)),
            "orbital": round_float(value.get("orbital", 1.0)),
            "vertical": round_float(value.get("vertical", 1.0)),
            "turbulence": round_float(value.get("turbulence", 1.0)),
            "shell": round_float(value.get("shell", 1.0)),
        }

    if isinstance(value, list):
        padded = list(value[:5]) + [1.0] * max(0, 5 - len(value))
        return {name: round_float(padded[index]) for index, name in enumerate(names)}

    return {name: 1.0 for name in names}


def extract_runtime_lifecycle(runtime_state: Dict[str, Any], control_state: Dict[str, Any]) -> Dict[str, Any]:
    runtime_mode = deep_get(
        runtime_state,
        [
            ["runtime_mode"],
            ["mode"],
            ["state", "runtime_mode"],
            ["runtime", "runtime_mode"],
        ],
        None,
    )

    if runtime_mode is None:
        runtime_mode = deep_get(
            control_state,
            [
                ["runtime_mode"],
                ["runtime", "runtime_mode"],
                ["state", "runtime_mode"],
            ],
            "unknown",
        )

    physics_armed = deep_get(
        runtime_state,
        [
            ["physics_armed"],
            ["armed"],
            ["runtime", "physics_armed"],
            ["state", "physics_armed"],
        ],
        None,
    )

    if physics_armed is None:
        physics_armed = deep_get(
            control_state,
            [
                ["physics_armed"],
                ["runtime", "physics_armed"],
                ["state", "physics_armed"],
            ],
            False,
        )

    simulation_paused = deep_get(
        runtime_state,
        [
            ["simulation_paused"],
            ["paused"],
            ["runtime", "simulation_paused"],
            ["state", "simulation_paused"],
        ],
        None,
    )

    if simulation_paused is None:
        simulation_paused = deep_get(
            control_state,
            [
                ["simulation_paused"],
                ["paused"],
                ["runtime", "simulation_paused"],
                ["state", "simulation_paused"],
            ],
            True,
        )

    geospatial_enabled = deep_get(
        runtime_state,
        [
            ["geospatial_enabled"],
            ["runtime", "geospatial_enabled"],
            ["state", "geospatial_enabled"],
        ],
        deep_get(
            control_state,
            [
                ["geospatial_enabled"],
                ["runtime", "geospatial_enabled"],
            ],
            False,
        ),
    )

    return {
        "runtime_mode": str(runtime_mode),
        "physics_armed": bool(physics_armed),
        "simulation_paused": bool(simulation_paused),
        "geospatial_enabled": bool(geospatial_enabled),
        "startup_complete": True,
        "shutdown_requested": False,
        "authority": "renderer_runtime",
    }


def extract_dataset_status(dataset_state: Dict[str, Any], dataset_meta: Dict[str, Any]) -> Dict[str, Any]:
    loaded = bool(
        deep_get(
            dataset_state,
            [
                ["loaded"],
                ["dataset", "loaded"],
                ["state", "loaded"],
            ],
            dataset_meta.get("loaded", False),
        )
    )

    enabled = bool(
        deep_get(
            dataset_state,
            [
                ["enabled"],
                ["dataset", "enabled"],
                ["state", "enabled"],
            ],
            loaded,
        )
    )

    fallback_active = bool(
        deep_get(
            dataset_state,
            [
                ["fallback_active"],
                ["dataset", "fallback_active"],
                ["state", "fallback_active"],
            ],
            False,
        )
    )

    row_count = safe_int(
        deep_get(
            dataset_state,
            [
                ["row_count"],
                ["dataset", "row_count"],
                ["registry", "row_count"],
                ["metadata", "row_count"],
            ],
            0,
        ),
        0,
    )

    mode = str(
        deep_get(
            dataset_state,
            [
                ["mode"],
                ["dataset", "mode"],
                ["state", "mode"],
            ],
            "unknown",
        )
    )

    source_csv = deep_get(
        dataset_state,
        [
            ["source_csv"],
            ["dataset", "source_csv"],
            ["metadata", "source_csv"],
        ],
        "",
    )

    return {
        "enabled": enabled,
        "loaded": loaded,
        "mode": mode,
        "row_count": row_count,
        "fallback_active": fallback_active,
        "source_csv": str(source_csv),
    }


def extract_species_status(root: Path) -> Dict[str, Any]:
    candidates = [
        root / "data" / "processed" / "species_identity_v1_6A_manifest.json",
        root / "data" / "processed" / "species_identity_manifest.json",
        root / "output" / "species_identity_manifest.json",
    ]

    manifest_data: Dict[str, Any] = {}
    manifest_path = ""

    for candidate in candidates:
        data, meta = read_json_file(candidate)
        if meta.get("loaded"):
            manifest_data = data
            manifest_path = str(candidate)
            break

    records = safe_int(
        deep_get(
            manifest_data,
            [
                ["records"],
                ["record_count"],
                ["particle_count"],
                ["row_count"],
            ],
            0,
        )
    )

    species_count = safe_int(
        deep_get(
            manifest_data,
            [
                ["species_count"],
                ["species", "count"],
            ],
            22,
        ),
        22,
    )

    sidecar_candidates = [
        root / "data" / "processed" / "species_identity_v1_6A.bin",
        root / "data" / "processed" / "species_identity.bin",
        root / "output" / "species_identity_v1_6A.bin",
    ]

    sidecar_path = ""
    sidecar_exists = False
    sidecar_size = 0

    for candidate in sidecar_candidates:
        if candidate.exists():
            sidecar_path = str(candidate)
            sidecar_exists = True
            try:
                sidecar_size = candidate.stat().st_size
            except OSError:
                sidecar_size = 0
            break

    return {
        "loaded": sidecar_exists,
        "manifest_loaded": bool(manifest_data),
        "manifest_path": manifest_path,
        "sidecar_path": sidecar_path,
        "sidecar_size_bytes": sidecar_size,
        "records": records,
        "species_count": species_count,
        "authority": "species_identity_sidecar" if sidecar_exists else "crab_default_fallback",
    }


def resolve_behavior(
    runtime_state: Dict[str, Any],
    behavior_state: Dict[str, Any],
    channels: Dict[str, Dict[str, Any]],
    vcv_fresh: bool,
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    gate_voltage = channel_scalar(channels, "/ch/19", 0.0, prefer_mapped=False)
    gate_threshold = safe_float(
        deep_get(
            schema,
            [["domains", "behavior", "vcv_gate_threshold_volts"]],
            5.0,
        ),
        5.0,
    )

    vcv_gate_active = vcv_fresh and gate_voltage >= gate_threshold

    # Prefer mapped behavior code if present. If only raw 0-10V exists, map to 0-7.
    ch18_entry = channels.get("/ch/18", {})
    if isinstance(ch18_entry, dict) and "mapped" in ch18_entry:
        vcv_code = safe_int(ch18_entry.get("mapped"), 0)
    else:
        raw_code_voltage = channel_scalar(channels, "/ch/18", 0.0, prefer_mapped=False)
        vcv_code = int(round(clamp(raw_code_voltage, 0.0, 10.0) / 10.0 * 7.0))

    vcv_code = int(clamp(float(vcv_code), 0.0, 7.0))

    manual_code = safe_int(
        deep_get(
            runtime_state,
            [
                ["behavior_effect_code"],
                ["behavior_code"],
                ["behavior", "code"],
                ["state", "behavior_effect_code"],
                ["state", "behavior_code"],
            ],
            deep_get(
                behavior_state,
                [
                    ["behavior_effect_code"],
                    ["behavior_code"],
                    ["code"],
                    ["behavior", "code"],
                ],
                0,
            ),
        ),
        0,
    )

    manual_enabled = bool(
        deep_get(
            runtime_state,
            [
                ["behavior_enabled"],
                ["behavior", "enabled"],
                ["state", "behavior_enabled"],
            ],
            deep_get(
                behavior_state,
                [
                    ["behavior_enabled"],
                    ["enabled"],
                    ["behavior", "enabled"],
                ],
                True,
            ),
        )
    )

    if vcv_gate_active:
        source = "vcv"
        effective_code = vcv_code
        enabled = effective_code != 0
        reason = "vcv_gate_ge_threshold"
    else:
        source = "manual"
        effective_code = int(clamp(float(manual_code), 0.0, 7.0))
        enabled = bool(manual_enabled) and effective_code != 0
        reason = "vcv_gate_inactive_or_stale"

    return {
        "authority": {
            "source": source,
            "gate_channel": "/ch/19",
            "gate_voltage": round_float(gate_voltage),
            "gate_threshold": round_float(gate_threshold),
            "fallback": "manual",
            "reason": reason,
            "vcv_fresh": vcv_fresh,
        },
        "effective": {
            "enabled": enabled,
            "code": effective_code,
            "name": behavior_name(effective_code, schema),
        },
        "manual": {
            "enabled": manual_enabled,
            "code": manual_code,
            "name": behavior_name(manual_code, schema),
        },
        "vcv": {
            "gate_active": vcv_gate_active,
            "code": vcv_code,
            "name": behavior_name(vcv_code, schema),
        },
    }


def resolve_field(
    runtime_state: Dict[str, Any],
    control_state: Dict[str, Any],
    channels: Dict[str, Dict[str, Any]],
    vcv_fresh: bool,
    schema: Dict[str, Any],
) -> Dict[str, Any]:
    # /ch/8 is scene index. If mapped exists, use it. Otherwise raw 0-10V maps to 0-7.
    ch8_entry = channels.get("/ch/8", {})
    if isinstance(ch8_entry, dict) and "mapped" in ch8_entry:
        scene_index = safe_int(ch8_entry.get("mapped"), 0)
    else:
        raw_scene_voltage = channel_scalar(channels, "/ch/8", 0.0, prefer_mapped=False)
        scene_index = int(round(clamp(raw_scene_voltage, 0.0, 10.0) / 10.0 * 7.0))

    scene_index = int(clamp(float(scene_index), 0.0, 7.0))

    runtime_weights = deep_get(
        runtime_state,
        [
            ["field_weights"],
            ["field", "weights"],
            ["effective_field_weights"],
            ["state", "field_weights"],
        ],
        None,
    )

    control_weights = deep_get(
        control_state,
        [
            ["field_weights"],
            ["field", "weights"],
            ["vcv", "field_weights"],
            ["state", "field_weights"],
        ],
        None,
    )

    recipe = field_recipe_for_scene(scene_index, schema)

    if vcv_fresh:
        source = "vcv_scene_channel"
        reason = "vcv_fresh_scene_channel"
        effective = recipe
    elif runtime_weights is not None:
        source = "runtime_state"
        reason = "vcv_stale_runtime_weights"
        effective = {
            "scene_index": scene_index,
            "recipe_name": "runtime_state_weights",
            "weights": normalize_field_weights(runtime_weights),
        }
    elif control_weights is not None:
        source = "control_state_compatibility"
        reason = "vcv_stale_control_weights"
        effective = {
            "scene_index": scene_index,
            "recipe_name": "control_state_weights",
            "weights": normalize_field_weights(control_weights),
        }
    else:
        source = "default"
        reason = "no_live_field_source"
        effective = field_recipe_for_scene(0, schema)

    return {
        "authority": {
            "source": source,
            "channel": "/ch/8",
            "fallback": "last_valid_or_default",
            "reason": reason,
            "vcv_fresh": vcv_fresh,
        },
        "effective": effective,
    }


def resolve_gravity(
    channels: Dict[str, Dict[str, Any]],
    vcv_fresh: bool,
) -> Dict[str, Any]:
    position_voices = channel_voices(channels, "/ch/14", max_count=4)
    padded_position = (position_voices + [0.0, 0.0, 0.0, 0.0])[:4]

    # If raw -5 to +5 appears, map into -1 to +1.
    mapped_position = []
    for value in padded_position:
        if -1.25 <= value <= 1.25:
            mapped_position.append(round_float(value))
        else:
            mapped_position.append(round_float(remap_bipolar_to_range(value, -1.0, 1.0)))

    ch15_entry = channels.get("/ch/15", {})
    if isinstance(ch15_entry, dict) and "mapped" in ch15_entry:
        strength = safe_float(ch15_entry.get("mapped"), 0.0)
    else:
        raw_strength = channel_scalar(channels, "/ch/15", 0.0, prefer_mapped=False)
        if 0.0 <= raw_strength <= 12.0:
            strength = raw_strength
        else:
            strength = remap_bipolar_to_range(raw_strength, 0.0, 12.0)

    source = "vcv" if vcv_fresh and (position_voices or strength != 0.0) else "internal"

    return {
        "authority": {
            "source": source,
            "position_channel": "/ch/14",
            "strength_channel": "/ch/15",
            "fallback": "internal",
            "vcv_fresh": vcv_fresh,
        },
        "effective": {
            "well_position": mapped_position,
            "well_strength": round_float(strength),
            "source": source,
        },
    }


def resolve_species_banks(
    channels: Dict[str, Dict[str, Any]],
    vcv_fresh: bool,
    species_status: Dict[str, Any],
) -> Dict[str, Any]:
    mass_a = channel_voices(channels, "/ch/10", max_count=16)
    mass_b = channel_voices(channels, "/ch/11", max_count=6)
    speed_a = channel_voices(channels, "/ch/9", max_count=16)
    speed_b = channel_voices(channels, "/ch/30", max_count=6)
    turbulence_a = channel_voices(channels, "/ch/12", max_count=16)
    turbulence_b = channel_voices(channels, "/ch/31", max_count=6)
    cohesion_a = channel_voices(channels, "/ch/13", max_count=16)
    cohesion_b = channel_voices(channels, "/ch/32", max_count=6)

    mass = (mass_a + mass_b)[:22]
    speed = (speed_a + speed_b)[:22]
    turbulence = (turbulence_a + turbulence_b)[:22]
    cohesion = (cohesion_a + cohesion_b)[:22]

    has_species_vcv = vcv_fresh and (
        len(mass) > 1 or
        len(speed) > 1 or
        len(turbulence) > 1 or
        len(cohesion) > 1
    )

    return {
        "authority": {
            "species_identity_source": species_status.get("authority", "unknown"),
            "control_source": "vcv_poly_bank" if has_species_vcv else "species_defaults",
            "fallback": "species_defaults",
            "vcv_fresh": vcv_fresh,
            "bank_a_count": 16,
            "bank_b_count": 6,
            "species_count": 22,
        },
        "effective": {
            "species_count": safe_int(species_status.get("species_count"), 22),
            "identity_loaded": bool(species_status.get("loaded")),
            "records": safe_int(species_status.get("records"), 0),
            "mass_voice_count": len(mass),
            "speed_voice_count": len(speed),
            "turbulence_voice_count": len(turbulence),
            "cohesion_voice_count": len(cohesion),
            "mass_preview": [round_float(v) for v in mass[:6]],
            "speed_preview": [round_float(v) for v in speed[:6]],
            "turbulence_preview": [round_float(v) for v in turbulence[:6]],
            "cohesion_preview": [round_float(v) for v in cohesion[:6]],
        },
    }


def build_effective_state(root: Path, stale_ms: int) -> Dict[str, Any]:
    config_path = root / "config" / "authority_schema.json"

    runtime_path = root / "output" / "runtime_state.json"
    vcv_path = root / "output" / "vcv_state.json"
    dataset_path = root / "output" / "dataset_state.json"
    dataset_coupling_path = root / "output" / "dataset_coupling_state.json"
    behavior_path = root / "output" / "behavior_state.json"
    control_path = root / "output" / "control_state.json"

    schema, schema_meta = read_json_file(config_path)
    runtime_state, runtime_meta = read_json_file(runtime_path)
    vcv_state, vcv_meta = read_json_file(vcv_path)
    dataset_state, dataset_meta = read_json_file(dataset_path)
    dataset_coupling_state, dataset_coupling_meta = read_json_file(dataset_coupling_path)
    behavior_state, behavior_meta = read_json_file(behavior_path)
    control_state, control_meta = read_json_file(control_path)

    channels = extract_channels(vcv_state)
    vcv_fresh = detect_vcv_fresh(vcv_state, vcv_meta, stale_ms)

    lifecycle = extract_runtime_lifecycle(runtime_state, control_state)
    dataset_status = extract_dataset_status(dataset_state, dataset_meta)
    species_status = extract_species_status(root)

    behavior = resolve_behavior(runtime_state, behavior_state, channels, vcv_fresh, schema)
    field = resolve_field(runtime_state, control_state, channels, vcv_fresh, schema)
    gravity = resolve_gravity(channels, vcv_fresh)
    species = resolve_species_banks(channels, vcv_fresh, species_status)

    warnings: List[str] = []
    stale_sources: List[str] = []
    fallbacks_active: List[str] = []

    source_metas = {
        "runtime_state": runtime_meta,
        "vcv_state": vcv_meta,
        "dataset_state": dataset_meta,
        "dataset_coupling_state": dataset_coupling_meta,
        "behavior_state": behavior_meta,
        "control_state": control_meta,
    }

    for name, meta in source_metas.items():
        if not meta.get("exists"):
            warnings.append(f"{name}_missing")
        elif not meta.get("loaded"):
            warnings.append(f"{name}_unloaded")
        elif safe_int(meta.get("age_ms"), 0) > stale_ms:
            stale_sources.append(name)

    if not vcv_fresh:
        fallbacks_active.append("vcv_stale_or_unavailable")

    if dataset_status.get("fallback_active"):
        fallbacks_active.append("dataset_fallback_active")

    if not dataset_status.get("loaded"):
        fallbacks_active.append("dataset_not_loaded")

    if not species_status.get("loaded"):
        fallbacks_active.append("species_identity_fallback")

    vcv_summary = {
        "fresh": vcv_fresh,
        "schema": str(vcv_state.get("schema", vcv_state.get("version", "unknown"))),
        "version": str(vcv_state.get("version", "unknown")),
        "channels_seen": len(channels),
        "last_update_age_ms": safe_int(vcv_meta.get("age_ms"), 0),
        "path": str(vcv_path),
    }

    effective_state = {
        "schema": SCHEMA_VERSION,
        "version": PATCH_VERSION,
        "updated_by": "src/runtime/authority_resolver.py",
        "timestamp_utc": utc_now_iso(),
        "monotonic_ms": monotonic_ms(),
        "project_root": str(root),

        "lifecycle": lifecycle,

        "sources": {
            "schema_config": {
                "loaded": bool(schema_meta.get("loaded")),
                "path": str(config_path),
                "version": str(schema.get("version", "unknown")),
            },
            "vcv": vcv_summary,
            "dataset": dataset_status,
            "dataset_coupling": {
                "loaded": bool(dataset_coupling_meta.get("loaded")),
                "age_ms": safe_int(dataset_coupling_meta.get("age_ms"), 0),
                "path": str(dataset_coupling_path),
            },
            "behavior_latch": {
                "loaded": bool(behavior_meta.get("loaded")),
                "age_ms": safe_int(behavior_meta.get("age_ms"), 0),
                "path": str(behavior_path),
            },
            "control_compatibility": {
                "loaded": bool(control_meta.get("loaded")),
                "age_ms": safe_int(control_meta.get("age_ms"), 0),
                "path": str(control_path),
                "role": "legacy_composite_report_not_final_authority",
            },
            "species_identity": species_status,
        },

        "authority": {
            "runtime_lifecycle": {
                "source": lifecycle.get("authority", "renderer_runtime"),
                "fallback": "safe_paused",
            },
            "dataset_source": {
                "source": "dataset_loader",
                "fallback": "synthetic_or_last_valid",
            },
            "particle_positions": {
                "source": "metal_gpu_live_buffer",
                "seed": "crab_nav_csv" if dataset_status.get("loaded") else "unknown_or_fallback",
            },
            "species_identity": {
                "source": species_status.get("authority", "unknown"),
                "fallback": "crab_default",
            },
            "behavior": behavior["authority"],
            "field_recipe": field["authority"],
            "gravity": gravity["authority"],
            "species_control": species["authority"],
            "hud": {
                "source": "effective_state",
                "role": "display_only",
            },
        },

        "effective": {
            "behavior": behavior["effective"],
            "field": field["effective"],
            "gravity": gravity["effective"],
            "species": species["effective"],
            "particles": {
                "count": safe_int(dataset_status.get("row_count"), safe_int(species_status.get("records"), 0)),
                "seed_source": dataset_status.get("mode", "unknown"),
                "live_owner": "metal_gpu",
                "reset_pending": bool(
                    deep_get(
                        runtime_state,
                        [
                            ["reset_pending"],
                            ["commands", "reset_pending"],
                            ["state", "reset_pending"],
                        ],
                        False,
                    )
                ),
                "respawn_on_capture": bool(
                    deep_get(
                        runtime_state,
                        [
                            ["respawn_on_capture"],
                            ["particles", "respawn_on_capture"],
                            ["state", "respawn_on_capture"],
                        ],
                        True,
                    )
                ),
            },
        },

        "raw_runtime_inputs": {
            "behavior": {
                "manual": behavior["manual"],
                "vcv": behavior["vcv"],
            },
            "vcv_channels_preview": summarize_channels(channels),
        },

        "diagnostics": {
            "warnings": warnings,
            "stale_sources": stale_sources,
            "fallbacks_active": fallbacks_active,
            "last_apply_stage": "authority_resolver_v1.7A",
            "hud_schema": "authority_truth_v1",
            "source_file_meta": source_metas,
        },
    }

    return effective_state


def summarize_channels(channels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    interesting = [
        "/ch/1", "/ch/2", "/ch/3", "/ch/4", "/ch/5", "/ch/6", "/ch/7", "/ch/8",
        "/ch/9", "/ch/10", "/ch/11", "/ch/12", "/ch/13", "/ch/14", "/ch/15",
        "/ch/16", "/ch/17", "/ch/18", "/ch/19", "/ch/28", "/ch/29", "/ch/30",
        "/ch/31", "/ch/32",
    ]

    for channel in interesting:
        entry = channels.get(channel)
        if not isinstance(entry, dict):
            continue

        voices = channel_voices(channels, channel)
        summary[channel] = {
            "label": str(entry.get("label", "")),
            "raw": round_float(entry.get("raw", entry.get("value", 0.0))),
            "mapped": round_float(entry.get("mapped", entry.get("value", entry.get("raw", 0.0)))),
            "voice_count": len(voices),
            "voices_preview": [round_float(v) for v in voices[:6]],
        }

    return summary


def print_status(payload: Dict[str, Any]) -> None:
    lifecycle = payload.get("lifecycle", {})
    effective = payload.get("effective", {})
    authority = payload.get("authority", {})
    sources = payload.get("sources", {})
    diagnostics = payload.get("diagnostics", {})

    behavior = effective.get("behavior", {})
    field = effective.get("field", {})
    vcv = sources.get("vcv", {})
    dataset = sources.get("dataset", {})
    species = sources.get("species_identity", {})

    print(
        "[RMU v1.7A Authority] "
        f"mode={lifecycle.get('runtime_mode')} "
        f"armed={lifecycle.get('physics_armed')} "
        f"paused={lifecycle.get('simulation_paused')} "
        f"vcv_fresh={vcv.get('fresh')} "
        f"dataset_rows={dataset.get('row_count')} "
        f"species_loaded={species.get('loaded')} "
        f"behavior={behavior.get('code')}:{behavior.get('name')} "
        f"behavior_src={authority.get('behavior', {}).get('source')} "
        f"field={field.get('scene_index')}:{field.get('recipe_name')} "
        f"fallbacks={','.join(diagnostics.get('fallbacks_active', [])) or 'none'}"
    )


def run_resolver(root: Path, once: bool, interval: float, stale_ms: int, quiet: bool) -> int:
    output_path = root / "output" / "effective_state.json"
    log_path = root / "output" / "logs" / "authority_resolver.log"

    root.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not quiet:
        print("============================================================")
        print("RealMathUniverse v1.7A Authority Resolver")
        print(f"Project root: {root}")
        print(f"Output:       {output_path}")
        print(f"Interval:     {interval:.3f}s")
        print(f"Stale ms:     {stale_ms}")
        print("============================================================")

    while True:
        try:
            payload = build_effective_state(root, stale_ms)
            atomic_write_json(output_path, payload)

            with log_path.open("a", encoding="utf-8") as log:
                log.write(
                    f"{payload.get('timestamp_utc')} "
                    f"mode={payload.get('lifecycle', {}).get('runtime_mode')} "
                    f"vcv_fresh={payload.get('sources', {}).get('vcv', {}).get('fresh')} "
                    f"behavior={payload.get('effective', {}).get('behavior', {}).get('code')} "
                    f"field={payload.get('effective', {}).get('field', {}).get('scene_index')} "
                    f"fallbacks={','.join(payload.get('diagnostics', {}).get('fallbacks_active', [])) or 'none'}\n"
                )

            if not quiet:
                print_status(payload)

            if once:
                return 0

            time.sleep(interval)

        except KeyboardInterrupt:
            if not quiet:
                print("\nAuthority resolver stopped.")
            return 0

        except Exception as exc:
            error_payload = {
                "schema": SCHEMA_VERSION,
                "version": PATCH_VERSION,
                "updated_by": "src/runtime/authority_resolver.py",
                "timestamp_utc": utc_now_iso(),
                "project_root": str(root),
                "fatal_error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
                "diagnostics": {
                    "warnings": ["authority_resolver_exception"],
                    "fallbacks_active": ["resolver_error"],
                },
            }

            try:
                atomic_write_json(output_path, error_payload)
            except Exception:
                pass

            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"{utc_now_iso()} ERROR {type(exc).__name__}: {exc}\n")

            if once:
                if not quiet:
                    print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
                return 1

            time.sleep(max(interval, 1.0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RealMathUniverse v1.7A authority resolver."
    )
    parser.add_argument(
        "--root",
        default=os.environ.get("RMU_ROOT", os.getcwd()),
        help="RealMathUniverse project root.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one authority resolution pass and exit.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="Loop interval in seconds.",
    )
    parser.add_argument(
        "--stale-ms",
        type=int,
        default=2500,
        help="State freshness threshold in milliseconds.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress normal console status lines.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    return run_resolver(
        root=root,
        once=bool(args.once),
        interval=max(0.05, float(args.interval)),
        stale_ms=max(100, int(args.stale_ms)),
        quiet=bool(args.quiet),
    )


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > scripts/run_authority_resolver.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Authority Resolver Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 src/runtime/authority_resolver.py --root "${PROJECT_ROOT}" --interval "${RMU_AUTHORITY_INTERVAL:-0.25}" --stale-ms "${RMU_AUTHORITY_STALE_MS:-2500}"
BASH

cat > scripts/run_metal_session_authority.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Single-Terminal Authority Session Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Run the new authority resolver in the background, then run the existing
#   RealMathUniverse Metal session command in the foreground.
#
# Usage:
#   ./scripts/run_metal_session_authority.sh preview 1920x1080
#
# Notes:
#   This wrapper does not replace the existing session runner.
#   It adds output/effective_state.json generation during the run.
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

mkdir -p output/logs

AUTHORITY_LOG="output/logs/authority_resolver_session.log"

echo "============================================================"
echo "RealMathUniverse v1.7A Authority Session"
echo "Project root: ${PROJECT_ROOT}"
echo "Authority log: ${AUTHORITY_LOG}"
echo "============================================================"

cleanup() {
  if [[ -n "${AUTHORITY_PID:-}" ]]; then
    if kill -0 "${AUTHORITY_PID}" >/dev/null 2>&1; then
      echo "Stopping authority resolver PID ${AUTHORITY_PID}"
      kill "${AUTHORITY_PID}" >/dev/null 2>&1 || true
      wait "${AUTHORITY_PID}" >/dev/null 2>&1 || true
    fi
  fi
}

trap cleanup EXIT INT TERM

python3 src/runtime/authority_resolver.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_AUTHORITY_INTERVAL:-0.25}" \
  --stale-ms "${RMU_AUTHORITY_STALE_MS:-2500}" \
  > "${AUTHORITY_LOG}" 2>&1 &

AUTHORITY_PID="$!"
echo "Started authority resolver PID ${AUTHORITY_PID}"

sleep 0.5

if [[ ! -x "./scripts/run_metal_session.sh" ]]; then
  echo "ERROR: ./scripts/run_metal_session.sh not found or not executable."
  echo "Run:"
  echo "  chmod +x ./scripts/run_metal_session.sh"
  exit 1
fi

echo "Launching existing Metal session:"
echo "  ./scripts/run_metal_session.sh $*"
echo "============================================================"

./scripts/run_metal_session.sh "$@"
BASH

cat > scripts/monitor_effective_state.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Effective State Monitor
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

STATE_FILE="output/effective_state.json"

if [[ ! -f "${STATE_FILE}" ]]; then
  echo "No ${STATE_FILE} found yet."
  echo "Start the resolver first:"
  echo "  ./scripts/run_authority_resolver.sh"
  exit 1
fi

while true; do
  clear
  echo "============================================================"
  echo "RealMathUniverse effective_state.json monitor"
  echo "============================================================"
  python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/effective_state.json")
try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"ERROR reading {path}: {exc}")
    raise SystemExit(1)

lifecycle = data.get("lifecycle", {})
sources = data.get("sources", {})
authority = data.get("authority", {})
effective = data.get("effective", {})
diagnostics = data.get("diagnostics", {})

behavior = effective.get("behavior", {})
field = effective.get("field", {})
gravity = effective.get("gravity", {})
particles = effective.get("particles", {})
vcv = sources.get("vcv", {})
dataset = sources.get("dataset", {})
species = sources.get("species_identity", {})

print(f"schema:        {data.get('schema')}")
print(f"version:       {data.get('version')}")
print(f"timestamp:     {data.get('timestamp_utc')}")
print()
print(f"runtime_mode:  {lifecycle.get('runtime_mode')}")
print(f"armed:         {lifecycle.get('physics_armed')}")
print(f"paused:        {lifecycle.get('simulation_paused')}")
print()
print(f"vcv fresh:     {vcv.get('fresh')}")
print(f"vcv version:   {vcv.get('version')}")
print(f"channels seen: {vcv.get('channels_seen')}")
print(f"vcv age ms:    {vcv.get('last_update_age_ms')}")
print()
print(f"dataset loaded:   {dataset.get('loaded')}")
print(f"dataset rows:     {dataset.get('row_count')}")
print(f"dataset mode:     {dataset.get('mode')}")
print(f"dataset fallback: {dataset.get('fallback_active')}")
print()
print(f"species loaded:   {species.get('loaded')}")
print(f"species records:  {species.get('records')}")
print(f"species count:    {species.get('species_count')}")
print()
print(f"behavior src:  {authority.get('behavior', {}).get('source')}")
print(f"behavior gate: {authority.get('behavior', {}).get('gate_voltage')}")
print(f"behavior:      {behavior.get('code')}  {behavior.get('name')}  enabled={behavior.get('enabled')}")
print()
print(f"field src:     {authority.get('field_recipe', {}).get('source')}")
print(f"scene index:   {field.get('scene_index')}")
print(f"field recipe:  {field.get('recipe_name')}")
print(f"field weights: {field.get('weights')}")
print()
print(f"gravity src:   {gravity.get('source')}")
print(f"gravity pos:   {gravity.get('well_position')}")
print(f"gravity str:   {gravity.get('well_strength')}")
print()
print(f"particles:     {particles.get('count')}")
print(f"live owner:    {particles.get('live_owner')}")
print(f"seed source:   {particles.get('seed_source')}")
print()
print(f"warnings:      {diagnostics.get('warnings')}")
print(f"stale sources: {diagnostics.get('stale_sources')}")
print(f"fallbacks:     {diagnostics.get('fallbacks_active')}")
PY

  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
BASH

chmod +x src/runtime/authority_resolver.py
chmod +x scripts/run_authority_resolver.sh
chmod +x scripts/run_metal_session_authority.sh
chmod +x scripts/monitor_effective_state.sh

echo "Running one resolver validation pass..."
python3 src/runtime/authority_resolver.py --root "${PROJECT_ROOT}" --once || {
  echo "ERROR: Authority resolver validation failed."
  exit 1
}

if [[ ! -f "output/effective_state.json" ]]; then
  echo "ERROR: output/effective_state.json was not created."
  exit 1
fi

echo "Validating output/effective_state.json JSON syntax..."
python3 -m json.tool output/effective_state.json >/dev/null

echo "============================================================"
echo "v1.7A Authority Schema Foundation installed successfully."
echo "Created:"
echo "  config/authority_schema.json"
echo "  src/runtime/authority_resolver.py"
echo "  scripts/run_authority_resolver.sh"
echo "  scripts/run_metal_session_authority.sh"
echo "  scripts/monitor_effective_state.sh"
echo "  output/effective_state.json"
echo "============================================================"
echo
echo "Test command:"
echo "  cat output/effective_state.json | python3 -m json.tool | head -80"
echo
echo "Single-terminal run command:"
echo "  ./scripts/run_metal_session_authority.sh preview 1920x1080"
echo
echo "Monitor command:"
echo "  ./scripts/monitor_effective_state.sh"
echo "============================================================"
