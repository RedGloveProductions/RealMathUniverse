#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7C Manual Authority Lock Installer
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Hard-lock field, scene, behavior, and camera authority to manual control by
#   default. VCV cannot rapidly switch fields/behaviors unless auto mode is
#   explicitly enabled through a control file.
#
# Why:
#   v1.7B stabilized values, but the bridge/renderer path can still consume live
#   VCV changes too quickly. This patch freezes the dangerous authority domains:
#
#     /ch/2  radial field
#     /ch/3  orbital field
#     /ch/4  vertical field
#     /ch/5  turbulence field
#     /ch/6  shell field
#     /ch/8  scene / field recipe
#     /ch/18 behavior code
#     /ch/19 behavior authority gate
#
#   Manual mode is default.
#
# New files:
#   config/manual_authority_lock.json
#   src/runtime/manual_authority_lock.py
#   scripts/run_manual_authority_lock.sh
#   scripts/run_metal_session_manual_locked.sh
#   scripts/rmu_auto_on.sh
#   scripts/rmu_auto_off.sh
#   scripts/rmu_set_manual_field.sh
#   scripts/rmu_set_manual_behavior.sh
#   scripts/monitor_manual_authority_lock.sh
#
# Runtime files:
#   output/manual_authority_mode.json
#   output/manual_authority_lock_state.json
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"

echo "============================================================"
echo "RealMathUniverse v1.7C Manual Authority Lock Installer"
echo "Project root: ${PROJECT_ROOT}"
echo "============================================================"

if [[ ! -d "${PROJECT_ROOT}" ]]; then
  echo "ERROR: Project root not found: ${PROJECT_ROOT}"
  exit 1
fi

cd "${PROJECT_ROOT}"

mkdir -p config
mkdir -p src/runtime
mkdir -p scripts
mkdir -p output
mkdir -p output/logs
mkdir -p output/backups/v1_7C_manual_authority_lock

STAMP="$(date +"%Y%m%d_%H%M%S")"

backup_if_exists() {
  local file_path="$1"
  if [[ -f "${file_path}" ]]; then
    local safe_name
    safe_name="$(echo "${file_path}" | sed 's#/#__#g')"
    cp "${file_path}" "output/backups/v1_7C_manual_authority_lock/${safe_name}.${STAMP}.bak"
    echo "Backed up ${file_path}"
  fi
}

backup_if_exists "config/manual_authority_lock.json"
backup_if_exists "src/runtime/manual_authority_lock.py"
backup_if_exists "scripts/run_manual_authority_lock.sh"
backup_if_exists "scripts/run_metal_session_manual_locked.sh"
backup_if_exists "scripts/rmu_auto_on.sh"
backup_if_exists "scripts/rmu_auto_off.sh"
backup_if_exists "scripts/rmu_set_manual_field.sh"
backup_if_exists "scripts/rmu_set_manual_behavior.sh"
backup_if_exists "scripts/monitor_manual_authority_lock.sh"

cat > config/manual_authority_lock.json <<'JSON'
{
  "schema": "rmu.manual_authority_lock.v1",
  "version": "1.7C-manual-authority-lock",
  "description": "Hard manual authority lock for fields, scene, behavior, and camera. Auto mode must be explicitly enabled.",
  "default_mode": {
    "auto_fields_enabled": false,
    "auto_behavior_enabled": false,
    "auto_camera_enabled": false
  },
  "manual_defaults": {
    "scene_index": 0,
    "behavior_code": 0,
    "field_weights": {
      "radial": 1.0,
      "orbital": 1.0,
      "vertical": 1.0,
      "turbulence": 1.0,
      "shell": 1.0
    }
  },
  "auto_timing": {
    "field_hold_ms": 30000,
    "field_min_change_interval_ms": 45000,
    "behavior_hold_ms": 30000,
    "behavior_min_change_interval_ms": 45000,
    "gate_hold_ms": 10000,
    "gate_on_threshold": 6.0,
    "gate_off_threshold": 4.0
  },
  "locked_channels": {
    "/ch/2": {
      "label": "radial",
      "manual_value": 1.0,
      "locked_unless_auto_fields": true
    },
    "/ch/3": {
      "label": "orbital",
      "manual_value": 1.0,
      "locked_unless_auto_fields": true
    },
    "/ch/4": {
      "label": "vertical",
      "manual_value": 1.0,
      "locked_unless_auto_fields": true
    },
    "/ch/5": {
      "label": "turbulence",
      "manual_value": 1.0,
      "locked_unless_auto_fields": true
    },
    "/ch/6": {
      "label": "shell",
      "manual_value": 1.0,
      "locked_unless_auto_fields": true
    },
    "/ch/8": {
      "label": "scene_index",
      "manual_value": 0,
      "locked_unless_auto_fields": true
    },
    "/ch/18": {
      "label": "behavior_code",
      "manual_value": 0,
      "locked_unless_auto_behavior": true
    },
    "/ch/19": {
      "label": "behavior_authority_gate",
      "manual_value": 0,
      "locked_unless_auto_behavior": true
    }
  },
  "camera": {
    "manual_locked": true,
    "camera_authority": "keyboard_mouse",
    "behavior_may_not_switch_camera": true,
    "scene_may_not_switch_camera": true
  }
}
JSON

cat > output/manual_authority_mode.json <<'JSON'
{
  "schema": "rmu.manual_authority_mode.v1",
  "version": "1.7C-manual-authority-lock",
  "auto_fields_enabled": false,
  "auto_behavior_enabled": false,
  "auto_camera_enabled": false,
  "manual_scene_index": 0,
  "manual_behavior_code": 0,
  "manual_field_weights": {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
  },
  "notes": "Manual authority is default. Use scripts/rmu_auto_on.sh to enable slow auto mode and scripts/rmu_auto_off.sh to return to manual lock."
}
JSON

cat > src/runtime/manual_authority_lock.py <<'PY'
#!/usr/bin/env python3
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7C Manual Authority Lock
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Hard-lock dangerous authority domains to manual mode unless auto mode is
#   explicitly enabled:
#
#     /ch/2  radial field
#     /ch/3  orbital field
#     /ch/4  vertical field
#     /ch/5  turbulence field
#     /ch/6  shell field
#     /ch/8  scene / field recipe
#     /ch/18 behavior code
#     /ch/19 behavior authority gate
#
# Design:
#   VCV remains active for other controls, including species banks, mass, speed,
#   gravity, color, etc. This file only locks the channels causing unstable
#   field snapping, behavior machine-gunning, and camera changes.
#
# Manual mode:
#   Fields, scene, behavior, and camera are manual. The lock writes stabilized
#   values back into output/vcv_state.json so the existing renderer sees fixed
#   authority values.
#
# Auto mode:
#   If output/manual_authority_mode.json sets auto_fields_enabled or
#   auto_behavior_enabled to true, the corresponding channels are allowed to
#   update, but only through very slow latching.
#
# 3P's:
#   Purpose:
#     Stop field/behavior/camera authority flicker immediately.
#
#   Parameters:
#     --root
#     --interval
#     --once
#     --quiet
#
#   Product:
#     output/vcv_state.json with manual-locked authority channels.
#     output/manual_authority_lock_state.json with diagnostics.
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


PATCH_VERSION = "1.7C-manual-authority-lock"


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_ms() -> int:
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


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd = -1
    tmp_path: Optional[Path] = None

    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            text=True
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


def read_json(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        if not path.exists():
            return {}, f"missing: {path}"
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {}, f"root is {type(data).__name__}, expected object"
        return data, None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def normalize_channel_key(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    if text.startswith("/ch/"):
        return text

    if text.startswith("ch/"):
        return "/" + text

    if text.startswith("ch") and text[2:].isdigit():
        return f"/ch/{int(text[2:])}"

    if text.startswith("channel_") and text.replace("channel_", "").isdigit():
        return f"/ch/{int(text.replace('channel_', ''))}"

    if text.isdigit():
        return f"/ch/{int(text)}"

    return text


def ensure_vcv_shape(data: Dict[str, Any]) -> None:
    if not isinstance(data.get("channels"), dict):
        data["channels"] = {}
    if not isinstance(data.get("direct_channels"), dict):
        data["direct_channels"] = {}
    if not isinstance(data.get("mapped_values"), dict):
        data["mapped_values"] = {}
    if not isinstance(data.get("labels"), dict):
        data["labels"] = {}


def set_channel_value(
    data: Dict[str, Any],
    channel: str,
    label: str,
    value: float,
    raw_value: Optional[float] = None,
    locked: bool = True,
    source: str = "manual_authority_lock"
) -> None:
    ensure_vcv_shape(data)

    if raw_value is None:
        raw_value = value

    entry = {
        "label": label,
        "raw": raw_value,
        "mapped": value,
        "value": value,
        "stable": value,
        "locked": locked,
        "source": source,
        "stabilized": True,
        "stabilized_by": PATCH_VERSION
    }

    data["channels"][channel] = copy.deepcopy(entry)
    data["direct_channels"][channel] = copy.deepcopy(entry)
    data["mapped_values"][label] = value
    data["labels"][channel] = label

    # Compatibility keys for older renderer variants.
    data[label] = value

    clean_ch = channel.replace("/ch/", "ch")
    data[clean_ch] = copy.deepcopy(entry)


def get_channel_raw(data: Dict[str, Any], channel: str, label: str, default: float = 0.0) -> float:
    containers = [
        data.get("channels"),
        data.get("direct_channels"),
        data.get("raw_channels"),
        data.get("values")
    ]

    for container in containers:
        if not isinstance(container, dict):
            continue

        for raw_key, raw_entry in container.items():
            key = normalize_channel_key(raw_key)
            if key != channel:
                continue

            if isinstance(raw_entry, dict):
                for field in ["raw", "value", "mapped", "stable"]:
                    if field in raw_entry:
                        value = raw_entry.get(field)
                        if isinstance(value, list) and value:
                            return safe_float(value[0], default)
                        return safe_float(value, default)
            else:
                return safe_float(raw_entry, default)

    mapped = data.get("mapped_values")
    if isinstance(mapped, dict) and label in mapped:
        return safe_float(mapped.get(label), default)

    if label in data:
        return safe_float(data.get(label), default)

    return default


def voltage_to_step(value: float, min_step: int = 0, max_step: int = 7) -> int:
    # If the value already looks like a step, treat it as one.
    if 0.0 <= value <= float(max_step) and abs(value - round(value)) < 0.001:
        return int(clamp(round(value), min_step, max_step))

    normalized = clamp(value / 10.0, 0.0, 1.0)
    step = int(round(min_step + normalized * (max_step - min_step)))
    return int(clamp(step, min_step, max_step))


# -----------------------------------------------------------------------------
# Manual mode and slow auto state
# -----------------------------------------------------------------------------

def default_mode() -> Dict[str, Any]:
    return {
        "schema": "rmu.manual_authority_mode.v1",
        "version": PATCH_VERSION,
        "auto_fields_enabled": False,
        "auto_behavior_enabled": False,
        "auto_camera_enabled": False,
        "manual_scene_index": 0,
        "manual_behavior_code": 0,
        "manual_field_weights": {
            "radial": 1.0,
            "orbital": 1.0,
            "vertical": 1.0,
            "turbulence": 1.0,
            "shell": 1.0
        }
    }


def load_mode(path: Path) -> Dict[str, Any]:
    data, error = read_json(path)
    if error or not data:
        mode = default_mode()
        atomic_write_json(path, mode)
        return mode

    merged = default_mode()
    merged.update(data)

    if not isinstance(merged.get("manual_field_weights"), dict):
        merged["manual_field_weights"] = default_mode()["manual_field_weights"]

    return merged


def default_lock_state() -> Dict[str, Any]:
    t = now_ms()
    return {
        "schema": "rmu.manual_authority_lock_state.v1",
        "version": PATCH_VERSION,
        "created_utc": utc_now_iso(),
        "channels": {
            "/ch/8": {
                "stable": 0,
                "candidate": 0,
                "candidate_since_ms": t,
                "last_change_ms": 0
            },
            "/ch/18": {
                "stable": 0,
                "candidate": 0,
                "candidate_since_ms": t,
                "last_change_ms": 0
            },
            "/ch/19": {
                "stable": 0,
                "candidate": 0,
                "candidate_since_ms": t,
                "last_change_ms": 0
            }
        }
    }


def load_lock_state(path: Path) -> Dict[str, Any]:
    data, error = read_json(path)
    if error or not data:
        return default_lock_state()

    if not isinstance(data.get("channels"), dict):
        data["channels"] = default_lock_state()["channels"]

    return data


def slow_latch_step(
    lock_state: Dict[str, Any],
    channel: str,
    candidate: int,
    hold_ms: int,
    min_change_interval_ms: int,
    fallback: int
) -> int:
    current_ms = now_ms()
    channels = lock_state.setdefault("channels", {})
    state = channels.setdefault(
        channel,
        {
            "stable": fallback,
            "candidate": fallback,
            "candidate_since_ms": current_ms,
            "last_change_ms": 0
        }
    )

    stable = safe_int(state.get("stable"), fallback)
    old_candidate = safe_int(state.get("candidate"), fallback)
    candidate_since = safe_int(state.get("candidate_since_ms"), current_ms)
    last_change = safe_int(state.get("last_change_ms"), 0)

    if candidate != old_candidate:
        state["candidate"] = candidate
        state["candidate_since_ms"] = current_ms
        state["candidate_age_ms"] = 0
        state["accepted_change"] = False
        return stable

    candidate_age = current_ms - candidate_since
    change_age = current_ms - last_change if last_change else 999999999

    if candidate != stable and candidate_age >= hold_ms and change_age >= min_change_interval_ms:
        stable = candidate
        state["stable"] = stable
        state["last_change_ms"] = current_ms
        state["accepted_change"] = True
    else:
        state["accepted_change"] = False

    state["candidate_age_ms"] = candidate_age
    state["change_age_ms"] = change_age
    state["last_seen_ms"] = current_ms

    return stable


def slow_latch_gate(
    lock_state: Dict[str, Any],
    channel: str,
    raw_voltage: float,
    hold_ms: int,
    on_threshold: float,
    off_threshold: float
) -> int:
    current_ms = now_ms()
    channels = lock_state.setdefault("channels", {})
    state = channels.setdefault(
        channel,
        {
            "stable": 0,
            "candidate": 0,
            "candidate_since_ms": current_ms,
            "last_change_ms": 0
        }
    )

    stable = safe_int(state.get("stable"), 0)

    if stable:
        candidate = 0 if raw_voltage <= off_threshold else 1
    else:
        candidate = 1 if raw_voltage >= on_threshold else 0

    old_candidate = safe_int(state.get("candidate"), 0)
    candidate_since = safe_int(state.get("candidate_since_ms"), current_ms)

    if candidate != old_candidate:
        state["candidate"] = candidate
        state["candidate_since_ms"] = current_ms
        state["candidate_age_ms"] = 0
        state["accepted_change"] = False
        return stable

    candidate_age = current_ms - candidate_since

    if candidate != stable and candidate_age >= hold_ms:
        stable = candidate
        state["stable"] = stable
        state["last_change_ms"] = current_ms
        state["accepted_change"] = True
    else:
        state["accepted_change"] = False

    state["candidate_age_ms"] = candidate_age
    state["last_seen_ms"] = current_ms
    state["raw_voltage"] = raw_voltage

    return stable


def apply_manual_or_slow_auto(
    root: Path,
    vcv_data: Dict[str, Any],
    config: Dict[str, Any],
    mode: Dict[str, Any],
    lock_state: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    data = copy.deepcopy(vcv_data)
    ensure_vcv_shape(data)

    auto_fields = bool(mode.get("auto_fields_enabled", False))
    auto_behavior = bool(mode.get("auto_behavior_enabled", False))
    auto_camera = bool(mode.get("auto_camera_enabled", False))

    manual_weights = mode.get("manual_field_weights")
    if not isinstance(manual_weights, dict):
        manual_weights = {}

    timing = config.get("auto_timing")
    if not isinstance(timing, dict):
        timing = {}

    # -------------------------------------------------------------------------
    # Fields and scene
    # -------------------------------------------------------------------------
    if not auto_fields:
        radial = safe_float(manual_weights.get("radial"), 1.0)
        orbital = safe_float(manual_weights.get("orbital"), 1.0)
        vertical = safe_float(manual_weights.get("vertical"), 1.0)
        turbulence = safe_float(manual_weights.get("turbulence"), 1.0)
        shell = safe_float(manual_weights.get("shell"), 1.0)
        scene = safe_int(mode.get("manual_scene_index"), 0)

        set_channel_value(data, "/ch/2", "radial", radial, locked=True)
        set_channel_value(data, "/ch/3", "orbital", orbital, locked=True)
        set_channel_value(data, "/ch/4", "vertical", vertical, locked=True)
        set_channel_value(data, "/ch/5", "turbulence", turbulence, locked=True)
        set_channel_value(data, "/ch/6", "shell", shell, locked=True)
        set_channel_value(data, "/ch/8", "scene_index", float(scene), locked=True)

        field_source = "manual_locked"
        scene_source = "manual_locked"

    else:
        raw_scene = get_channel_raw(data, "/ch/8", "scene_index", 0.0)
        candidate_scene = voltage_to_step(raw_scene, 0, 7)

        scene = slow_latch_step(
            lock_state=lock_state,
            channel="/ch/8",
            candidate=candidate_scene,
            hold_ms=safe_int(timing.get("field_hold_ms"), 30000),
            min_change_interval_ms=safe_int(timing.get("field_min_change_interval_ms"), 45000),
            fallback=safe_int(mode.get("manual_scene_index"), 0)
        )

        set_channel_value(
            data,
            "/ch/8",
            "scene_index",
            float(scene),
            raw_value=raw_scene,
            locked=False,
            source="slow_auto_fields"
        )

        field_source = "slow_auto_fields"
        scene_source = "slow_auto_fields"

    # -------------------------------------------------------------------------
    # Behavior
    # -------------------------------------------------------------------------
    if not auto_behavior:
        behavior = safe_int(mode.get("manual_behavior_code"), 0)

        set_channel_value(data, "/ch/18", "behavior_code", float(behavior), locked=True)
        set_channel_value(data, "/ch/19", "behavior_authority_gate", 0.0, locked=True)

        behavior_source = "manual_locked"
        gate_source = "manual_locked"

    else:
        raw_behavior = get_channel_raw(data, "/ch/18", "behavior_code", 0.0)
        candidate_behavior = voltage_to_step(raw_behavior, 0, 7)

        behavior = slow_latch_step(
            lock_state=lock_state,
            channel="/ch/18",
            candidate=candidate_behavior,
            hold_ms=safe_int(timing.get("behavior_hold_ms"), 30000),
            min_change_interval_ms=safe_int(timing.get("behavior_min_change_interval_ms"), 45000),
            fallback=safe_int(mode.get("manual_behavior_code"), 0)
        )

        raw_gate = get_channel_raw(data, "/ch/19", "behavior_authority_gate", 0.0)

        gate_state = slow_latch_gate(
            lock_state=lock_state,
            channel="/ch/19",
            raw_voltage=raw_gate,
            hold_ms=safe_int(timing.get("gate_hold_ms"), 10000),
            on_threshold=safe_float(timing.get("gate_on_threshold"), 6.0),
            off_threshold=safe_float(timing.get("gate_off_threshold"), 4.0)
        )

        gate_voltage = 10.0 if gate_state else 0.0

        set_channel_value(
            data,
            "/ch/18",
            "behavior_code",
            float(behavior),
            raw_value=raw_behavior,
            locked=False,
            source="slow_auto_behavior"
        )

        set_channel_value(
            data,
            "/ch/19",
            "behavior_authority_gate",
            gate_voltage,
            raw_value=raw_gate,
            locked=False,
            source="slow_auto_behavior_gate"
        )

        behavior_source = "slow_auto_behavior"
        gate_source = "slow_auto_behavior_gate"

    # -------------------------------------------------------------------------
    # Camera metadata
    # -------------------------------------------------------------------------
    data["manual_authority_lock"] = {
        "schema": "rmu.manual_authority_lock.runtime.v1",
        "version": PATCH_VERSION,
        "updated_utc": utc_now_iso(),
        "auto_fields_enabled": auto_fields,
        "auto_behavior_enabled": auto_behavior,
        "auto_camera_enabled": auto_camera,
        "field_source": field_source,
        "scene_source": scene_source,
        "behavior_source": behavior_source,
        "gate_source": gate_source,
        "camera": {
            "authority": "auto" if auto_camera else "keyboard_mouse",
            "manual_locked": not auto_camera,
            "behavior_may_not_switch_camera": True,
            "scene_may_not_switch_camera": True
        }
    }

    data["stabilized_schema"] = "rmu.vcv_state_manual_locked.v1"
    data["stabilized_version"] = PATCH_VERSION
    data["stabilized_by"] = "src/runtime/manual_authority_lock.py"
    data["stabilized_utc"] = utc_now_iso()

    lock_state["version"] = PATCH_VERSION
    lock_state["updated_utc"] = utc_now_iso()
    lock_state["mode"] = {
        "auto_fields_enabled": auto_fields,
        "auto_behavior_enabled": auto_behavior,
        "auto_camera_enabled": auto_camera
    }
    lock_state["effective"] = {
        "scene_index": safe_int(data["mapped_values"].get("scene_index"), 0),
        "behavior_code": safe_int(data["mapped_values"].get("behavior_code"), 0),
        "behavior_gate": safe_float(data["mapped_values"].get("behavior_authority_gate"), 0.0),
        "field_weights": {
            "radial": safe_float(data["mapped_values"].get("radial"), 1.0),
            "orbital": safe_float(data["mapped_values"].get("orbital"), 1.0),
            "vertical": safe_float(data["mapped_values"].get("vertical"), 1.0),
            "turbulence": safe_float(data["mapped_values"].get("turbulence"), 1.0),
            "shell": safe_float(data["mapped_values"].get("shell"), 1.0)
        }
    }

    return data, lock_state


def run_lock(root: Path, interval: float, once: bool, quiet: bool) -> int:
    config_path = root / "config" / "manual_authority_lock.json"
    mode_path = root / "output" / "manual_authority_mode.json"
    vcv_path = root / "output" / "vcv_state.json"
    raw_path = root / "output" / "vcv_state_before_manual_lock.json"
    locked_path = root / "output" / "vcv_state_manual_locked.json"
    state_path = root / "output" / "manual_authority_lock_state.json"
    log_path = root / "output" / "logs" / "manual_authority_lock.log"

    config, config_error = read_json(config_path)
    if config_error:
        print(f"ERROR: could not read {config_path}: {config_error}")
        return 1

    lock_state = load_lock_state(state_path)

    if not quiet:
        print("============================================================")
        print("RealMathUniverse v1.7C Manual Authority Lock")
        print(f"Project root: {root}")
        print(f"Input/output: {vcv_path}")
        print(f"Mode file:    {mode_path}")
        print("============================================================")

    while True:
        try:
            mode = load_mode(mode_path)
            vcv_data, vcv_error = read_json(vcv_path)

            if vcv_error:
                if not quiet:
                    print(f"[manual-lock] waiting for vcv_state.json: {vcv_error}")
                if once:
                    return 1
                time.sleep(interval)
                continue

            raw_copy = copy.deepcopy(vcv_data)
            raw_copy["preserved_before_manual_lock_by"] = PATCH_VERSION
            raw_copy["preserved_before_manual_lock_utc"] = utc_now_iso()
            atomic_write_json(raw_path, raw_copy)

            locked_data, lock_state = apply_manual_or_slow_auto(
                root=root,
                vcv_data=vcv_data,
                config=config,
                mode=mode,
                lock_state=lock_state
            )

            atomic_write_json(locked_path, locked_data)
            atomic_write_json(state_path, lock_state)

            # Hard write-back for current renderer compatibility.
            atomic_write_json(vcv_path, locked_data)

            eff = lock_state.get("effective", {})
            mode_summary = lock_state.get("mode", {})

            with log_path.open("a", encoding="utf-8") as log:
                log.write(
                    f"{utc_now_iso()} "
                    f"auto_fields={mode_summary.get('auto_fields_enabled')} "
                    f"auto_behavior={mode_summary.get('auto_behavior_enabled')} "
                    f"scene={eff.get('scene_index')} "
                    f"behavior={eff.get('behavior_code')} "
                    f"gate={eff.get('behavior_gate')} "
                    f"fields={eff.get('field_weights')}\n"
                )

            if not quiet:
                print(
                    "[RMU v1.7C Manual Lock] "
                    f"auto_fields={mode_summary.get('auto_fields_enabled')} "
                    f"auto_behavior={mode_summary.get('auto_behavior_enabled')} "
                    f"scene={eff.get('scene_index')} "
                    f"behavior={eff.get('behavior_code')} "
                    f"gate={eff.get('behavior_gate')} "
                    f"fields={eff.get('field_weights')}"
                )

            if once:
                return 0

            time.sleep(interval)

        except KeyboardInterrupt:
            if not quiet:
                print("\nManual authority lock stopped.")
            return 0

        except Exception as exc:
            try:
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"{utc_now_iso()} ERROR {type(exc).__name__}: {exc}\n")
            except Exception:
                pass

            if not quiet:
                print(f"ERROR: {type(exc).__name__}: {exc}")

            if once:
                return 1

            time.sleep(max(interval, 0.05))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.7C manual authority lock.")
    parser.add_argument(
        "--root",
        default=os.environ.get("RMU_ROOT", os.getcwd()),
        help="RealMathUniverse project root."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.02,
        help="Loop interval in seconds. Default is 0.02 for hard lock enforcement."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce console output."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    return run_lock(
        root=root,
        interval=max(0.01, float(args.interval)),
        once=bool(args.once),
        quiet=bool(args.quiet)
    )


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > scripts/run_manual_authority_lock.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7C Manual Authority Lock Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 src/runtime/manual_authority_lock.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_MANUAL_LOCK_INTERVAL:-0.02}"
BASH

cat > scripts/run_metal_session_manual_locked.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7C Manual-Locked Session Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Starts:
#   1. v1.7A authority resolver, if present
#   2. v1.7C manual authority lock
#   3. existing Metal session runner
#
# Usage:
#   ./scripts/run_metal_session_manual_locked.sh preview 1920x1080
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
MANUAL_LOCK_LOG="output/logs/manual_authority_lock_session.log"

echo "============================================================"
echo "RealMathUniverse v1.7C Manual-Locked Session"
echo "Project root: ${PROJECT_ROOT}"
echo "Authority log: ${AUTHORITY_LOG}"
echo "Manual lock log: ${MANUAL_LOCK_LOG}"
echo "============================================================"

cleanup() {
  if [[ -n "${AUTHORITY_PID:-}" ]]; then
    if kill -0 "${AUTHORITY_PID}" >/dev/null 2>&1; then
      echo "Stopping authority resolver PID ${AUTHORITY_PID}"
      kill "${AUTHORITY_PID}" >/dev/null 2>&1 || true
      wait "${AUTHORITY_PID}" >/dev/null 2>&1 || true
    fi
  fi

  if [[ -n "${MANUAL_LOCK_PID:-}" ]]; then
    if kill -0 "${MANUAL_LOCK_PID}" >/dev/null 2>&1; then
      echo "Stopping manual authority lock PID ${MANUAL_LOCK_PID}"
      kill "${MANUAL_LOCK_PID}" >/dev/null 2>&1 || true
      wait "${MANUAL_LOCK_PID}" >/dev/null 2>&1 || true
    fi
  fi
}

trap cleanup EXIT INT TERM

# Make manual mode explicit at session start.
python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/manual_authority_mode.json")
if path.exists():
    data = json.loads(path.read_text())
else:
    data = {}

data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7C-manual-authority-lock"
data["auto_fields_enabled"] = False
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("manual_field_weights", {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
})

path.write_text(json.dumps(data, indent=2) + "\n")
print("Manual authority mode forced ON at session start.")
PY

if [[ -f "src/runtime/authority_resolver.py" ]]; then
  python3 src/runtime/authority_resolver.py \
    --root "${PROJECT_ROOT}" \
    --interval "${RMU_AUTHORITY_INTERVAL:-0.25}" \
    --stale-ms "${RMU_AUTHORITY_STALE_MS:-2500}" \
    > "${AUTHORITY_LOG}" 2>&1 &

  AUTHORITY_PID="$!"
  echo "Started authority resolver PID ${AUTHORITY_PID}"
else
  echo "WARNING: src/runtime/authority_resolver.py not found. Continuing without v1.7A resolver."
fi

python3 src/runtime/manual_authority_lock.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_MANUAL_LOCK_INTERVAL:-0.02}" \
  > "${MANUAL_LOCK_LOG}" 2>&1 &

MANUAL_LOCK_PID="$!"
echo "Started manual authority lock PID ${MANUAL_LOCK_PID}"

sleep 0.75

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

cat > scripts/rmu_auto_on.sh <<'BASH'
#!/usr/bin/env bash
# Enable very slow auto mode for fields and behavior.

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/manual_authority_mode.json")
data = json.loads(path.read_text()) if path.exists() else {}

data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7C-manual-authority-lock"
data["auto_fields_enabled"] = True
data["auto_behavior_enabled"] = True
data["auto_camera_enabled"] = False
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("manual_field_weights", {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
})

path.write_text(json.dumps(data, indent=2) + "\n")
print("AUTO MODE ENABLED: fields and behavior may change slowly. Camera remains manual.")
PY
BASH

cat > scripts/rmu_auto_off.sh <<'BASH'
#!/usr/bin/env bash
# Disable auto mode. Fields, behavior, and camera return to manual lock.

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/manual_authority_mode.json")
data = json.loads(path.read_text()) if path.exists() else {}

data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7C-manual-authority-lock"
data["auto_fields_enabled"] = False
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("manual_field_weights", {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
})

path.write_text(json.dumps(data, indent=2) + "\n")
print("AUTO MODE OFF: manual field, behavior, and camera authority locked.")
PY
BASH

cat > scripts/rmu_set_manual_field.sh <<'BASH'
#!/usr/bin/env bash
# Set manual scene/field index and optional field weights.
#
# Usage:
#   ./scripts/rmu_set_manual_field.sh 0
#   ./scripts/rmu_set_manual_field.sh 4
#   ./scripts/rmu_set_manual_field.sh 0 1.0 1.0 1.0 0.2 1.0
#
# Args:
#   $1 scene index 0-7
#   $2 radial weight optional
#   $3 orbital weight optional
#   $4 vertical weight optional
#   $5 turbulence weight optional
#   $6 shell weight optional

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

SCENE="${1:-0}"
RADIAL="${2:-}"
ORBITAL="${3:-}"
VERTICAL="${4:-}"
TURBULENCE="${5:-}"
SHELL="${6:-}"

python3 - "$SCENE" "$RADIAL" "$ORBITAL" "$VERTICAL" "$TURBULENCE" "$SHELL" <<'PY'
import json
import sys
from pathlib import Path

scene = int(float(sys.argv[1]))
radial = sys.argv[2]
orbital = sys.argv[3]
vertical = sys.argv[4]
turbulence = sys.argv[5]
shell = sys.argv[6]

path = Path("output/manual_authority_mode.json")
data = json.loads(path.read_text()) if path.exists() else {}

data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7C-manual-authority-lock"
data["auto_fields_enabled"] = False
data["auto_camera_enabled"] = False
data["manual_scene_index"] = max(0, min(7, scene))

weights = data.setdefault("manual_field_weights", {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
})

def maybe_set(name, value):
    if value != "":
        weights[name] = float(value)

maybe_set("radial", radial)
maybe_set("orbital", orbital)
maybe_set("vertical", vertical)
maybe_set("turbulence", turbulence)
maybe_set("shell", shell)

path.write_text(json.dumps(data, indent=2) + "\n")

print(f"Manual field locked: scene_index={data['manual_scene_index']}, weights={weights}")
PY
BASH

cat > scripts/rmu_set_manual_behavior.sh <<'BASH'
#!/usr/bin/env bash
# Set manual behavior code and keep auto behavior OFF.
#
# Usage:
#   ./scripts/rmu_set_manual_behavior.sh 0
#   ./scripts/rmu_set_manual_behavior.sh 5

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

BEHAVIOR="${1:-0}"

python3 - "$BEHAVIOR" <<'PY'
import json
import sys
from pathlib import Path

behavior = int(float(sys.argv[1]))

path = Path("output/manual_authority_mode.json")
data = json.loads(path.read_text()) if path.exists() else {}

data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7C-manual-authority-lock"
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data["manual_behavior_code"] = max(0, min(7, behavior))

path.write_text(json.dumps(data, indent=2) + "\n")

print(f"Manual behavior locked: behavior_code={data['manual_behavior_code']}")
PY
BASH

cat > scripts/monitor_manual_authority_lock.sh <<'BASH'
#!/usr/bin/env bash
# Monitor v1.7C manual authority lock.

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

while true; do
  clear
  echo "============================================================"
  echo "RealMathUniverse v1.7C Manual Authority Lock Monitor"
  echo "============================================================"

  python3 - <<'PY'
import json
from pathlib import Path

mode_path = Path("output/manual_authority_mode.json")
state_path = Path("output/manual_authority_lock_state.json")
vcv_path = Path("output/vcv_state.json")

def load(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        return {"error": str(exc)}

mode = load(mode_path)
state = load(state_path)
vcv = load(vcv_path)

print("MODE")
print(f"  auto_fields_enabled:   {mode.get('auto_fields_enabled')}")
print(f"  auto_behavior_enabled: {mode.get('auto_behavior_enabled')}")
print(f"  auto_camera_enabled:   {mode.get('auto_camera_enabled')}")
print(f"  manual_scene_index:    {mode.get('manual_scene_index')}")
print(f"  manual_behavior_code:  {mode.get('manual_behavior_code')}")
print(f"  manual_field_weights:  {mode.get('manual_field_weights')}")
print()

print("LOCK EFFECTIVE")
eff = state.get("effective", {})
print(f"  scene_index:      {eff.get('scene_index')}")
print(f"  behavior_code:    {eff.get('behavior_code')}")
print(f"  behavior_gate:    {eff.get('behavior_gate')}")
print(f"  field_weights:    {eff.get('field_weights')}")
print()

print("VCV STATE CHECK")
mapped = vcv.get("mapped_values", {})
print(f"  /ch/2 radial:     {mapped.get('radial')}")
print(f"  /ch/3 orbital:    {mapped.get('orbital')}")
print(f"  /ch/4 vertical:   {mapped.get('vertical')}")
print(f"  /ch/5 turbulence: {mapped.get('turbulence')}")
print(f"  /ch/6 shell:      {mapped.get('shell')}")
print(f"  /ch/8 scene:      {mapped.get('scene_index')}")
print(f"  /ch/18 behavior:  {mapped.get('behavior_code')}")
print(f"  /ch/19 gate:      {mapped.get('behavior_authority_gate')}")
print()

lock = vcv.get("manual_authority_lock", {})
print("CAMERA")
print(f"  camera authority:              {lock.get('camera', {}).get('authority')}")
print(f"  camera manual locked:          {lock.get('camera', {}).get('manual_locked')}")
print(f"  behavior may switch camera:    {lock.get('camera', {}).get('behavior_may_not_switch_camera') == False}")
print(f"  scene may switch camera:       {lock.get('camera', {}).get('scene_may_not_switch_camera') == False}")
print()

print(f"stabilized_version: {vcv.get('stabilized_version')}")
print(f"stabilized_utc:     {vcv.get('stabilized_utc')}")
PY

  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
BASH

chmod +x src/runtime/manual_authority_lock.py
chmod +x scripts/run_manual_authority_lock.sh
chmod +x scripts/run_metal_session_manual_locked.sh
chmod +x scripts/rmu_auto_on.sh
chmod +x scripts/rmu_auto_off.sh
chmod +x scripts/rmu_set_manual_field.sh
chmod +x scripts/rmu_set_manual_behavior.sh
chmod +x scripts/monitor_manual_authority_lock.sh

echo "Running one manual authority lock validation pass..."
python3 src/runtime/manual_authority_lock.py --root "${PROJECT_ROOT}" --once || {
  echo "WARNING: manual authority lock could not run once yet."
  echo "This usually means output/vcv_state.json does not exist until the simulator/VCV bridge has run."
  echo "The patch is still installed."
}

echo "============================================================"
echo "v1.7C Manual Authority Lock installed."
echo "============================================================"
echo
echo "Primary run command:"
echo "  cd ${PROJECT_ROOT}"
echo "  source .venv/bin/activate"
echo "  ./scripts/run_metal_session_manual_locked.sh preview 1920x1080"
echo
echo "Monitor:"
echo "  ./scripts/monitor_manual_authority_lock.sh"
echo
echo "Manual mode commands:"
echo "  ./scripts/rmu_auto_off.sh"
echo "  ./scripts/rmu_set_manual_field.sh 0"
echo "  ./scripts/rmu_set_manual_behavior.sh 0"
echo
echo "Slow auto mode command:"
echo "  ./scripts/rmu_auto_on.sh"
echo "============================================================"'
