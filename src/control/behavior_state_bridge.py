#!/usr/bin/env python3
"""
RealMathUniverse v1.2B3 behavior state bridge.

Purpose:
- Keep renderer-selected behavior_mode latched in output/control_state.json.
- Prevent high-frequency control-state writers from erasing behavior_mode.
- Preserve dataset and VCV blocks without changing their contracts.

Authority order:
1. output/behavior_state.json, written by the renderer when the user selects behavior.
2. Existing output/control_state.json behavior_mode if behavior_state does not exist.
3. stable_orbit_cloud default only when neither file contains a valid behavior.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(os.environ.get("RMU_PROJECT_ROOT", "/Users/Joe/Documents/RealMathUniverse"))
OUTPUT_DIR = PROJECT_ROOT / "output"
CONTROL_STATE_PATH = OUTPUT_DIR / "control_state.json"
BEHAVIOR_STATE_PATH = OUTPUT_DIR / "behavior_state.json"
VALID_BEHAVIORS = {
    "stable_orbit_cloud",
    "black_hole_capture",
    "accretion_disk",
    "field_pressure_bounce",
    "infinite_collapse",
}
DEFAULT_BEHAVIOR = "stable_orbit_cloud"


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
    tmp.replace(path)


def valid_behavior(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value in VALID_BEHAVIORS else None


def ensure_behavior_state() -> Dict[str, Any]:
    behavior_state = read_json(BEHAVIOR_STATE_PATH, {})
    if isinstance(behavior_state, dict):
        b = valid_behavior(behavior_state.get("behavior_mode"))
        if b:
            return behavior_state

    control_state = read_json(CONTROL_STATE_PATH, {})
    b = None
    if isinstance(control_state, dict):
        b = valid_behavior(control_state.get("behavior_mode"))
        if not b and isinstance(control_state.get("collapse_behavior"), dict):
            b = valid_behavior(control_state["collapse_behavior"].get("behavior_mode"))

    if not b:
        b = DEFAULT_BEHAVIOR

    now = time.time()
    behavior_state = {
        "version": "1.2B3",
        "behavior_mode": b,
        "behavior_source": "behavior_state_bridge_default" if b == DEFAULT_BEHAVIOR else "existing_control_state",
        "behavior_lock": True,
        "behavior_timestamp_unix": now,
        "updated_by": "behavior_state_bridge_v1_2B3",
        "collapse_behavior": {
            "behavior_mode": b,
            "source": "behavior_state_bridge_default" if b == DEFAULT_BEHAVIOR else "existing_control_state",
            "locked": True,
            "timestamp_unix": now,
        },
        "timestamp_unix": now,
    }
    atomic_write_json(BEHAVIOR_STATE_PATH, behavior_state)
    return behavior_state


def merge_behavior_into_control() -> Dict[str, Any]:
    behavior_state = ensure_behavior_state()
    behavior = valid_behavior(behavior_state.get("behavior_mode")) or DEFAULT_BEHAVIOR
    source = behavior_state.get("behavior_source", "behavior_state_bridge")
    locked = bool(behavior_state.get("behavior_lock", True))
    behavior_ts = behavior_state.get("behavior_timestamp_unix", time.time())

    control_state = read_json(CONTROL_STATE_PATH, {})
    if not isinstance(control_state, dict):
        control_state = {}

    before = json.dumps(control_state, sort_keys=True, default=str)

    control_state["behavior_mode"] = behavior
    control_state["behavior_source"] = source
    control_state["behavior_lock"] = locked
    control_state["behavior_timestamp_unix"] = behavior_ts
    control_state["collapse_behavior"] = {
        "behavior_mode": behavior,
        "source": source,
        "locked": locked,
        "timestamp_unix": behavior_ts,
    }
    control_state["behavior_persistence"] = {
        "version": "1.2B3",
        "status": "latched",
        "behavior_mode": behavior,
        "source": source,
        "lock": locked,
        "bridge_timestamp_unix": time.time(),
        "behavior_state_path": str(BEHAVIOR_STATE_PATH),
    }
    control_state["updated_by_behavior_state_bridge"] = "behavior_state_bridge_v1_2B3"
    control_state["behavior_state_bridge_timestamp_unix"] = time.time()

    after = json.dumps(control_state, sort_keys=True, default=str)
    if before != after:
        atomic_write_json(CONTROL_STATE_PATH, control_state)
    return control_state


def main() -> None:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.2B3 behavior state bridge")
    parser.add_argument("--once", action="store_true", help="merge behavior once and exit")
    parser.add_argument("--interval", type=float, default=0.10, help="seconds between merges")
    args = parser.parse_args()

    if args.once:
        state = merge_behavior_into_control()
        print(json.dumps({
            "behavior_mode": state.get("behavior_mode"),
            "behavior_source": state.get("behavior_source"),
            "behavior_lock": state.get("behavior_lock"),
            "status": "merged_once",
        }, indent=2, sort_keys=True))
        return

    print("RealMathUniverse v1.2B3 behavior state bridge running")
    print(f"project_root={PROJECT_ROOT}")
    while True:
        try:
            state = merge_behavior_into_control()
            print(f"behavior latched: {state.get('behavior_mode')} | source={state.get('behavior_source')}")
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"behavior bridge warning: {exc}")
        time.sleep(max(0.05, args.interval))


if __name__ == "__main__":
    main()
