#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B Stabilized Authority Inputs Installer
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Stabilize fast-changing VCV/runtime authority inputs before they destabilize
#   fields, behavior modes, and camera/scene state.
#
# Adds:
#   config/stabilization_schema.json
#   src/runtime/vcv_state_stabilizer.py
#   scripts/run_vcv_state_stabilizer.sh
#   scripts/run_metal_session_stable_authority.sh
#   scripts/monitor_stabilized_vcv_state.sh
#
# Runtime outputs:
#   output/vcv_state_raw.json
#   output/vcv_state_stable.json
#   output/vcv_state_stabilizer_state.json
#
# Important:
#   This patch runs as a compatibility stabilizer. It can write stabilized values
#   back into output/vcv_state.json so the existing Swift/Metal renderer sees
#   latched, debounced channels without needing a Swift patch yet.
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"

echo "============================================================"
echo "RealMathUniverse v1.7B Stabilized Authority Inputs Installer"
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
mkdir -p output/backups/v1_7B_stabilize_authority_inputs

STAMP="$(date +"%Y%m%d_%H%M%S")"

backup_if_exists() {
  local file_path="$1"
  if [[ -f "${file_path}" ]]; then
    local safe_name
    safe_name="$(echo "${file_path}" | sed 's#/#__#g')"
    cp "${file_path}" "output/backups/v1_7B_stabilize_authority_inputs/${safe_name}.${STAMP}.bak"
    echo "Backed up ${file_path}"
  fi
}

backup_if_exists "config/stabilization_schema.json"
backup_if_exists "src/runtime/vcv_state_stabilizer.py"
backup_if_exists "scripts/run_vcv_state_stabilizer.sh"
backup_if_exists "scripts/run_metal_session_stable_authority.sh"
backup_if_exists "scripts/monitor_stabilized_vcv_state.sh"

cat > config/stabilization_schema.json <<'JSON'
{
  "schema": "rmu.stabilization_schema.v1",
  "version": "1.7B-stabilized-authority-inputs",
  "description": "Debounce, latch, hysteresis, and rate-limit schema for VCV-driven scene, field, behavior, and camera stability.",
  "global": {
    "enabled": true,
    "write_back_to_vcv_state": true,
    "raw_copy_path": "output/vcv_state_raw.json",
    "stable_copy_path": "output/vcv_state_stable.json",
    "stabilizer_state_path": "output/vcv_state_stabilizer_state.json",
    "minimum_loop_interval_seconds": 0.05
  },
  "channels": {
    "/ch/8": {
      "label": "scene_index",
      "kind": "stepped_latched",
      "min_step": 0,
      "max_step": 7,
      "raw_voltage_min": 0.0,
      "raw_voltage_max": 10.0,
      "hold_ms": 1200,
      "min_change_interval_ms": 1800,
      "initial_value": 0,
      "purpose": "Scene and field recipe selector. Stabilized to prevent field-layer snapback and rapid recipe flicker."
    },
    "/ch/18": {
      "label": "behavior_code",
      "kind": "stepped_latched",
      "min_step": 0,
      "max_step": 7,
      "raw_voltage_min": 0.0,
      "raw_voltage_max": 10.0,
      "hold_ms": 900,
      "min_change_interval_ms": 1500,
      "initial_value": 0,
      "purpose": "Behavior selector. Stabilized to prevent behavior machine-gun switching."
    },
    "/ch/19": {
      "label": "behavior_authority_gate",
      "kind": "hysteresis_gate",
      "on_threshold": 5.5,
      "off_threshold": 4.5,
      "hold_ms": 500,
      "initial_value": 0,
      "purpose": "VCV behavior authority gate. Uses hysteresis so noisy voltage does not rapidly take/release authority."
    }
  },
  "camera": {
    "lock_camera_to_manual": true,
    "camera_authority": "keyboard_mouse",
    "camera_should_not_follow_behavior": true,
    "camera_should_not_follow_scene": true,
    "notes": "This writes explicit stabilization metadata. If the renderer still changes camera on behavior change, a Swift-side v1.7C patch must remove behavior-to-camera coupling."
  },
  "fields": {
    "prevent_snapback": true,
    "last_valid_scene_holds_when_vcv_stale": true,
    "scene_channel": "/ch/8"
  },
  "behavior": {
    "prevent_fast_swapping": true,
    "behavior_channel": "/ch/18",
    "authority_gate_channel": "/ch/19",
    "manual_fallback_when_gate_off": true
  }
}
JSON

cat > src/runtime/vcv_state_stabilizer.py <<'PY'
#!/usr/bin/env python3
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B VCV State Stabilizer
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Stabilize scene, field, behavior, and authority-gate channels before the
#   existing Swift/Metal renderer consumes output/vcv_state.json.
#
# Why this exists:
#   v1.7A created effective_state.json, but the current renderer still reads
#   legacy VCV/control state paths directly. This stabilizer provides an
#   immediate compatibility bridge by debouncing and latching the noisy/fast
#   channels that are causing field snapback, rapid behavior switching, and
#   camera/scene coupling symptoms.
#
# Stabilized channels:
#   /ch/8   scene_index / field recipe selector
#   /ch/18  behavior_code
#   /ch/19  behavior_authority_gate
#
# Outputs:
#   output/vcv_state_raw.json
#   output/vcv_state_stable.json
#   output/vcv_state_stabilizer_state.json
#
# Optional compatibility write-back:
#   --write-back rewrites output/vcv_state.json with stabilized values.
#
# 3P's:
#   Purpose:
#     Reduce state flicker and snapback before renderer consumption.
#
#   Parameters:
#     --root
#     --interval
#     --write-back
#     --once
#     --quiet
#
#   Product:
#     Stabilized VCV state files and optional stabilized output/vcv_state.json.
#
# Test:
#   python3 src/runtime/vcv_state_stabilizer.py --root . --once --write-back
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
from typing import Any, Dict, List, Optional, Tuple


PATCH_VERSION = "1.7B-stabilized-authority-inputs"


# -----------------------------------------------------------------------------
# Basic utilities
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
            return {}, f"root is {type(data).__name__}, expected dict"
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


def voltage_to_step(voltage: float, v_min: float, v_max: float, step_min: int, step_max: int) -> int:
    if v_max == v_min:
        return step_min

    n = (voltage - v_min) / (v_max - v_min)
    n = clamp(n, 0.0, 1.0)

    step = int(round(step_min + n * (step_max - step_min)))
    return int(clamp(float(step), float(step_min), float(step_max)))


def extract_channel_entry(data: Dict[str, Any], channel: str) -> Dict[str, Any]:
    possible_containers = [
        data.get("channels"),
        data.get("direct_channels"),
        data.get("raw_channels"),
        data.get("values")
    ]

    for container in possible_containers:
        if isinstance(container, dict):
            for raw_key, raw_entry in container.items():
                key = normalize_channel_key(raw_key)
                if key == channel:
                    if isinstance(raw_entry, dict):
                        return copy.deepcopy(raw_entry)
                    return {"raw": raw_entry, "value": raw_entry}

    # Top-level compatibility.
    if channel in data:
        entry = data[channel]
        if isinstance(entry, dict):
            return copy.deepcopy(entry)
        return {"raw": entry, "value": entry}

    labels = {
        "/ch/8": "scene_index",
        "/ch/18": "behavior_code",
        "/ch/19": "behavior_authority_gate"
    }

    label = labels.get(channel)
    mapped = data.get("mapped_values")
    if label and isinstance(mapped, dict) and label in mapped:
        return {"mapped": mapped[label], "label": label}

    if label and label in data:
        return {"mapped": data[label], "label": label}

    return {}


def extract_channel_voltage_or_mapped(data: Dict[str, Any], channel: str) -> Tuple[float, str]:
    entry = extract_channel_entry(data, channel)

    for key in ["raw", "value", "smoothed", "voltage"]:
        if key in entry:
            value = entry.get(key)
            if isinstance(value, list) and value:
                return safe_float(value[0]), key
            return safe_float(value), key

    for key in ["mapped"]:
        if key in entry:
            value = entry.get(key)
            if isinstance(value, list) and value:
                return safe_float(value[0]), key
            return safe_float(value), key

    voices = entry.get("voices")
    if isinstance(voices, list) and voices:
        return safe_float(voices[0]), "voices"

    return 0.0, "missing"


def ensure_channel_dicts(data: Dict[str, Any]) -> None:
    if not isinstance(data.get("channels"), dict):
        data["channels"] = {}
    if not isinstance(data.get("direct_channels"), dict):
        data["direct_channels"] = {}
    if not isinstance(data.get("mapped_values"), dict):
        data["mapped_values"] = {}
    if not isinstance(data.get("labels"), dict):
        data["labels"] = {}


def set_stabilized_channel(
    data: Dict[str, Any],
    channel: str,
    label: str,
    raw_value: float,
    mapped_value: float,
    stable_value: float,
    kind: str
) -> None:
    ensure_channel_dicts(data)

    entry = {
        "label": label,
        "raw": raw_value,
        "mapped": mapped_value,
        "value": stable_value,
        "stable": stable_value,
        "kind": kind,
        "stabilized": True,
        "stabilized_by": PATCH_VERSION
    }

    data["channels"][channel] = copy.deepcopy(entry)
    data["direct_channels"][channel] = copy.deepcopy(entry)
    data["mapped_values"][label] = stable_value
    data["labels"][channel] = label

    # Compatibility top-level keys for renderer variants.
    data[label] = stable_value

    clean_name = channel.replace("/ch/", "ch")
    data[clean_name] = copy.deepcopy(entry)


# -----------------------------------------------------------------------------
# Stabilizer state machine
# -----------------------------------------------------------------------------

def default_stabilizer_state() -> Dict[str, Any]:
    return {
        "schema": "rmu.vcv_state_stabilizer_state.v1",
        "version": PATCH_VERSION,
        "created_utc": utc_now_iso(),
        "channels": {
            "/ch/8": {
                "label": "scene_index",
                "stable": 0,
                "candidate": 0,
                "candidate_since_ms": 0,
                "last_change_ms": 0
            },
            "/ch/18": {
                "label": "behavior_code",
                "stable": 0,
                "candidate": 0,
                "candidate_since_ms": 0,
                "last_change_ms": 0
            },
            "/ch/19": {
                "label": "behavior_authority_gate",
                "stable": 0,
                "candidate": 0,
                "candidate_since_ms": 0,
                "last_change_ms": 0
            }
        },
        "camera": {
            "authority": "keyboard_mouse",
            "lock_camera_to_manual": True,
            "camera_should_not_follow_behavior": True,
            "camera_should_not_follow_scene": True
        }
    }


def load_or_create_state(path: Path) -> Dict[str, Any]:
    data, error = read_json(path)
    if error or not data:
        return default_stabilizer_state()

    if not isinstance(data.get("channels"), dict):
        data["channels"] = default_stabilizer_state()["channels"]

    return data


def update_stepped_latched(
    state: Dict[str, Any],
    channel: str,
    candidate_step: int,
    hold_ms: int,
    min_change_interval_ms: int,
    initial_value: int
) -> Tuple[int, Dict[str, Any]]:
    current_ms = now_ms()

    channels = state.setdefault("channels", {})
    ch_state = channels.setdefault(
        channel,
        {
            "stable": initial_value,
            "candidate": initial_value,
            "candidate_since_ms": current_ms,
            "last_change_ms": 0
        }
    )

    stable = safe_int(ch_state.get("stable"), initial_value)
    previous_candidate = safe_int(ch_state.get("candidate"), initial_value)
    candidate_since_ms = safe_int(ch_state.get("candidate_since_ms"), current_ms)
    last_change_ms = safe_int(ch_state.get("last_change_ms"), 0)

    if candidate_step != previous_candidate:
        ch_state["candidate"] = candidate_step
        ch_state["candidate_since_ms"] = current_ms
        ch_state["last_seen_ms"] = current_ms
        ch_state["changed_candidate"] = True
        return stable, ch_state

    candidate_age = current_ms - candidate_since_ms
    change_age = current_ms - last_change_ms if last_change_ms > 0 else 999999999

    if candidate_step != stable and candidate_age >= hold_ms and change_age >= min_change_interval_ms:
        stable = candidate_step
        ch_state["stable"] = stable
        ch_state["last_change_ms"] = current_ms
        ch_state["accepted_change"] = True
    else:
        ch_state["accepted_change"] = False

    ch_state["last_seen_ms"] = current_ms
    ch_state["candidate_age_ms"] = candidate_age
    ch_state["change_age_ms"] = change_age

    return stable, ch_state


def update_hysteresis_gate(
    state: Dict[str, Any],
    channel: str,
    voltage: float,
    on_threshold: float,
    off_threshold: float,
    hold_ms: int,
    initial_value: int
) -> Tuple[int, Dict[str, Any]]:
    current_ms = now_ms()

    channels = state.setdefault("channels", {})
    ch_state = channels.setdefault(
        channel,
        {
            "stable": initial_value,
            "candidate": initial_value,
            "candidate_since_ms": current_ms,
            "last_change_ms": 0
        }
    )

    stable = safe_int(ch_state.get("stable"), initial_value)

    if stable:
        candidate = 0 if voltage <= off_threshold else 1
    else:
        candidate = 1 if voltage >= on_threshold else 0

    previous_candidate = safe_int(ch_state.get("candidate"), initial_value)
    candidate_since_ms = safe_int(ch_state.get("candidate_since_ms"), current_ms)

    if candidate != previous_candidate:
        ch_state["candidate"] = candidate
        ch_state["candidate_since_ms"] = current_ms
        ch_state["last_seen_ms"] = current_ms
        ch_state["accepted_change"] = False
        return stable, ch_state

    candidate_age = current_ms - candidate_since_ms

    if candidate != stable and candidate_age >= hold_ms:
        stable = candidate
        ch_state["stable"] = stable
        ch_state["last_change_ms"] = current_ms
        ch_state["accepted_change"] = True
    else:
        ch_state["accepted_change"] = False

    ch_state["voltage"] = voltage
    ch_state["candidate_age_ms"] = candidate_age
    ch_state["last_seen_ms"] = current_ms

    return stable, ch_state


def stabilize_vcv_state(
    root: Path,
    raw_data: Dict[str, Any],
    schema: Dict[str, Any],
    stabilizer_state: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    stable_data = copy.deepcopy(raw_data)
    current_ms = now_ms()

    channels_cfg = schema.get("channels", {})
    if not isinstance(channels_cfg, dict):
        channels_cfg = {}

    # -------------------------------------------------------------------------
    # /ch/8 scene_index, stepped latch
    # -------------------------------------------------------------------------
    ch8_cfg = channels_cfg.get("/ch/8", {})
    ch8_raw, ch8_source = extract_channel_voltage_or_mapped(raw_data, "/ch/8")

    if ch8_source == "mapped":
        ch8_candidate = safe_int(ch8_raw, safe_int(ch8_cfg.get("initial_value"), 0))
    else:
        ch8_candidate = voltage_to_step(
            voltage=ch8_raw,
            v_min=safe_float(ch8_cfg.get("raw_voltage_min"), 0.0),
            v_max=safe_float(ch8_cfg.get("raw_voltage_max"), 10.0),
            step_min=safe_int(ch8_cfg.get("min_step"), 0),
            step_max=safe_int(ch8_cfg.get("max_step"), 7)
        )

    ch8_stable, ch8_state = update_stepped_latched(
        stabilizer_state,
        "/ch/8",
        ch8_candidate,
        hold_ms=safe_int(ch8_cfg.get("hold_ms"), 1200),
        min_change_interval_ms=safe_int(ch8_cfg.get("min_change_interval_ms"), 1800),
        initial_value=safe_int(ch8_cfg.get("initial_value"), 0)
    )

    set_stabilized_channel(
        stable_data,
        "/ch/8",
        "scene_index",
        raw_value=ch8_raw,
        mapped_value=float(ch8_candidate),
        stable_value=float(ch8_stable),
        kind="stepped_latched"
    )

    # -------------------------------------------------------------------------
    # /ch/18 behavior_code, stepped latch
    # -------------------------------------------------------------------------
    ch18_cfg = channels_cfg.get("/ch/18", {})
    ch18_raw, ch18_source = extract_channel_voltage_or_mapped(raw_data, "/ch/18")

    if ch18_source == "mapped":
        ch18_candidate = safe_int(ch18_raw, safe_int(ch18_cfg.get("initial_value"), 0))
    else:
        ch18_candidate = voltage_to_step(
            voltage=ch18_raw,
            v_min=safe_float(ch18_cfg.get("raw_voltage_min"), 0.0),
            v_max=safe_float(ch18_cfg.get("raw_voltage_max"), 10.0),
            step_min=safe_int(ch18_cfg.get("min_step"), 0),
            step_max=safe_int(ch18_cfg.get("max_step"), 7)
        )

    ch18_stable, ch18_state = update_stepped_latched(
        stabilizer_state,
        "/ch/18",
        ch18_candidate,
        hold_ms=safe_int(ch18_cfg.get("hold_ms"), 900),
        min_change_interval_ms=safe_int(ch18_cfg.get("min_change_interval_ms"), 1500),
        initial_value=safe_int(ch18_cfg.get("initial_value"), 0)
    )

    set_stabilized_channel(
        stable_data,
        "/ch/18",
        "behavior_code",
        raw_value=ch18_raw,
        mapped_value=float(ch18_candidate),
        stable_value=float(ch18_stable),
        kind="stepped_latched"
    )

    # -------------------------------------------------------------------------
    # /ch/19 behavior_authority_gate, hysteresis gate
    # -------------------------------------------------------------------------
    ch19_cfg = channels_cfg.get("/ch/19", {})
    ch19_raw, _ = extract_channel_voltage_or_mapped(raw_data, "/ch/19")

    ch19_stable, ch19_state = update_hysteresis_gate(
        stabilizer_state,
        "/ch/19",
        voltage=ch19_raw,
        on_threshold=safe_float(ch19_cfg.get("on_threshold"), 5.5),
        off_threshold=safe_float(ch19_cfg.get("off_threshold"), 4.5),
        hold_ms=safe_int(ch19_cfg.get("hold_ms"), 500),
        initial_value=safe_int(ch19_cfg.get("initial_value"), 0)
    )

    # Keep voltage visible, but stabilized mapped gate is 0 or 10.
    ch19_mapped_voltage = 10.0 if ch19_stable else 0.0

    set_stabilized_channel(
        stable_data,
        "/ch/19",
        "behavior_authority_gate",
        raw_value=ch19_raw,
        mapped_value=ch19_mapped_voltage,
        stable_value=ch19_mapped_voltage,
        kind="hysteresis_gate"
    )

    # -------------------------------------------------------------------------
    # Add explicit stabilization metadata.
    # -------------------------------------------------------------------------
    stable_data["schema"] = stable_data.get("schema", "rmu.vcv_state.compatibility")
    stable_data["stabilized_schema"] = "rmu.vcv_state_stable.v1"
    stable_data["stabilized_version"] = PATCH_VERSION
    stable_data["stabilized_utc"] = utc_now_iso()
    stable_data["stabilized_by"] = "src/runtime/vcv_state_stabilizer.py"

    stable_data["stabilization"] = {
        "version": PATCH_VERSION,
        "write_back_compatible": True,
        "camera": {
            "authority": "keyboard_mouse",
            "lock_camera_to_manual": True,
            "camera_should_not_follow_behavior": True,
            "camera_should_not_follow_scene": True
        },
        "channels": {
            "/ch/8": {
                "label": "scene_index",
                "raw": ch8_raw,
                "candidate": ch8_candidate,
                "stable": ch8_stable,
                "state": ch8_state
            },
            "/ch/18": {
                "label": "behavior_code",
                "raw": ch18_raw,
                "candidate": ch18_candidate,
                "stable": ch18_stable,
                "state": ch18_state
            },
            "/ch/19": {
                "label": "behavior_authority_gate",
                "raw": ch19_raw,
                "stable": ch19_stable,
                "mapped_voltage": ch19_mapped_voltage,
                "state": ch19_state
            }
        }
    }

    stabilizer_state["version"] = PATCH_VERSION
    stabilizer_state["updated_utc"] = utc_now_iso()
    stabilizer_state["updated_ms"] = current_ms
    stabilizer_state["camera"] = stable_data["stabilization"]["camera"]

    return stable_data, stabilizer_state


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------

def run_stabilizer(
    root: Path,
    interval: float,
    write_back: bool,
    once: bool,
    quiet: bool
) -> int:
    schema_path = root / "config" / "stabilization_schema.json"
    vcv_path = root / "output" / "vcv_state.json"
    raw_path = root / "output" / "vcv_state_raw.json"
    stable_path = root / "output" / "vcv_state_stable.json"
    state_path = root / "output" / "vcv_state_stabilizer_state.json"
    log_path = root / "output" / "logs" / "vcv_state_stabilizer.log"

    schema, schema_error = read_json(schema_path)
    if schema_error:
        print(f"ERROR: could not load {schema_path}: {schema_error}")
        return 1

    stabilizer_state = load_or_create_state(state_path)

    if not quiet:
        print("============================================================")
        print("RealMathUniverse v1.7B VCV State Stabilizer")
        print(f"Project root: {root}")
        print(f"Input:        {vcv_path}")
        print(f"Raw copy:     {raw_path}")
        print(f"Stable copy:  {stable_path}")
        print(f"Write back:   {write_back}")
        print("============================================================")

    while True:
        try:
            raw_data, raw_error = read_json(vcv_path)

            if raw_error:
                if not quiet:
                    print(f"[stabilizer] waiting for vcv_state.json: {raw_error}")
                if once:
                    return 1
                time.sleep(interval)
                continue

            # Preserve exact raw incoming state before stabilization.
            raw_copy = copy.deepcopy(raw_data)
            raw_copy["raw_preserved_by"] = PATCH_VERSION
            raw_copy["raw_preserved_utc"] = utc_now_iso()
            atomic_write_json(raw_path, raw_copy)

            stable_data, stabilizer_state = stabilize_vcv_state(
                root=root,
                raw_data=raw_data,
                schema=schema,
                stabilizer_state=stabilizer_state
            )

            atomic_write_json(stable_path, stable_data)
            atomic_write_json(state_path, stabilizer_state)

            if write_back:
                atomic_write_json(vcv_path, stable_data)

            with log_path.open("a", encoding="utf-8") as log:
                stab = stable_data.get("stabilization", {}).get("channels", {})
                ch8 = stab.get("/ch/8", {})
                ch18 = stab.get("/ch/18", {})
                ch19 = stab.get("/ch/19", {})
                log.write(
                    f"{utc_now_iso()} "
                    f"ch8_scene={ch8.get('stable')} "
                    f"ch18_behavior={ch18.get('stable')} "
                    f"ch19_gate={ch19.get('stable')} "
                    f"write_back={write_back}\n"
                )

            if not quiet:
                stab = stable_data.get("stabilization", {}).get("channels", {})
                ch8 = stab.get("/ch/8", {})
                ch18 = stab.get("/ch/18", {})
                ch19 = stab.get("/ch/19", {})
                print(
                    "[RMU v1.7B Stabilizer] "
                    f"scene={ch8.get('stable')} cand={ch8.get('candidate')} "
                    f"behavior={ch18.get('stable')} cand={ch18.get('candidate')} "
                    f"gate={ch19.get('stable')} raw={ch19.get('raw')} "
                    f"write_back={write_back}"
                )

            if once:
                return 0

            time.sleep(interval)

        except KeyboardInterrupt:
            if not quiet:
                print("\nVCV state stabilizer stopped.")
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

            time.sleep(max(interval, 0.25))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.7B VCV state stabilizer.")
    parser.add_argument(
        "--root",
        default=os.environ.get("RMU_ROOT", os.getcwd()),
        help="RealMathUniverse project root."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.10,
        help="Loop interval in seconds."
    )
    parser.add_argument(
        "--write-back",
        action="store_true",
        help="Write stabilized values back into output/vcv_state.json for current renderer compatibility."
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

    return run_stabilizer(
        root=root,
        interval=max(0.05, float(args.interval)),
        write_back=bool(args.write_back),
        once=bool(args.once),
        quiet=bool(args.quiet)
    )


if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > scripts/run_vcv_state_stabilizer.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B VCV State Stabilizer Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 src/runtime/vcv_state_stabilizer.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_STABILIZER_INTERVAL:-0.10}" \
  --write-back
BASH

cat > scripts/run_metal_session_stable_authority.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B Stable Authority Session Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Starts:
#   1. v1.7A authority resolver
#   2. v1.7B VCV state stabilizer with write-back
#   3. existing Metal session runner
#
# Usage:
#   ./scripts/run_metal_session_stable_authority.sh preview 1920x1080
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
STABILIZER_LOG="output/logs/vcv_state_stabilizer_session.log"

echo "============================================================"
echo "RealMathUniverse v1.7B Stable Authority Session"
echo "Project root: ${PROJECT_ROOT}"
echo "Authority log: ${AUTHORITY_LOG}"
echo "Stabilizer log: ${STABILIZER_LOG}"
echo "============================================================"

cleanup() {
  if [[ -n "${AUTHORITY_PID:-}" ]]; then
    if kill -0 "${AUTHORITY_PID}" >/dev/null 2>&1; then
      echo "Stopping authority resolver PID ${AUTHORITY_PID}"
      kill "${AUTHORITY_PID}" >/dev/null 2>&1 || true
      wait "${AUTHORITY_PID}" >/dev/null 2>&1 || true
    fi
  fi

  if [[ -n "${STABILIZER_PID:-}" ]]; then
    if kill -0 "${STABILIZER_PID}" >/dev/null 2>&1; then
      echo "Stopping VCV stabilizer PID ${STABILIZER_PID}"
      kill "${STABILIZER_PID}" >/dev/null 2>&1 || true
      wait "${STABILIZER_PID}" >/dev/null 2>&1 || true
    fi
  fi
}

trap cleanup EXIT INT TERM

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

python3 src/runtime/vcv_state_stabilizer.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_STABILIZER_INTERVAL:-0.10}" \
  --write-back \
  > "${STABILIZER_LOG}" 2>&1 &

STABILIZER_PID="$!"
echo "Started VCV state stabilizer PID ${STABILIZER_PID}"

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

cat > scripts/monitor_stabilized_vcv_state.sh <<'BASH'
#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B Stabilized VCV State Monitor
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

STATE_FILE="output/vcv_state_stable.json"

if [[ ! -f "${STATE_FILE}" ]]; then
  echo "No ${STATE_FILE} found yet."
  echo "Start the stabilizer first:"
  echo "  ./scripts/run_vcv_state_stabilizer.sh"
  exit 1
fi

while true; do
  clear
  echo "============================================================"
  echo "RealMathUniverse stabilized VCV monitor"
  echo "============================================================"
  python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/vcv_state_stable.json")
try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"ERROR reading {path}: {exc}")
    raise SystemExit(1)

stab = data.get("stabilization", {})
channels = stab.get("channels", {})
camera = stab.get("camera", {})

for ch in ["/ch/8", "/ch/18", "/ch/19"]:
    item = channels.get(ch, {})
    state = item.get("state", {})
    print(f"{ch}")
    print(f"  label:          {item.get('label')}")
    print(f"  raw:            {item.get('raw')}")
    print(f"  candidate:      {item.get('candidate')}")
    print(f"  stable:         {item.get('stable')}")
    print(f"  accepted:       {state.get('accepted_change')}")
    print(f"  candidate age:  {state.get('candidate_age_ms')}")
    print(f"  change age:     {state.get('change_age_ms')}")
    print()

print("camera")
print(f"  authority:                    {camera.get('authority')}")
print(f"  lock_camera_to_manual:         {camera.get('lock_camera_to_manual')}")
print(f"  should_not_follow_behavior:    {camera.get('camera_should_not_follow_behavior')}")
print(f"  should_not_follow_scene:       {camera.get('camera_should_not_follow_scene')}")
print()
print(f"stabilized version: {data.get('stabilized_version')}")
print(f"stabilized utc:     {data.get('stabilized_utc')}")
PY
  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
BASH

chmod +x src/runtime/vcv_state_stabilizer.py
chmod +x scripts/run_vcv_state_stabilizer.sh
chmod +x scripts/run_metal_session_stable_authority.sh
chmod +x scripts/monitor_stabilized_vcv_state.sh

echo "Running one stabilizer validation pass..."
python3 src/runtime/vcv_state_stabilizer.py --root "${PROJECT_ROOT}" --once --write-back || {
  echo "ERROR: v1.7B stabilizer validation failed."
  echo "This may be because output/vcv_state.json does not exist yet."
  echo "Run the simulator once, then run this installer again if needed."
  exit 1
}

python3 -m json.tool output/vcv_state_stable.json >/dev/null
python3 -m json.tool output/vcv_state_stabilizer_state.json >/dev/null

echo "============================================================"
echo "v1.7B Stabilized Authority Inputs installed successfully."
echo "Created:"
echo "  config/stabilization_schema.json"
echo "  src/runtime/vcv_state_stabilizer.py"
echo "  scripts/run_vcv_state_stabilizer.sh"
echo "  scripts/run_metal_session_stable_authority.sh"
echo "  scripts/monitor_stabilized_vcv_state.sh"
echo "  output/vcv_state_raw.json"
echo "  output/vcv_state_stable.json"
echo "  output/vcv_state_stabilizer_state.json"
echo "============================================================"
echo
echo "Run command:"
echo "  ./scripts/run_metal_session_stable_authority.sh preview 1920x1080"
echo
echo "Monitor command:"
echo "  ./scripts/monitor_stabilized_vcv_state.sh"
echo "============================================================"
