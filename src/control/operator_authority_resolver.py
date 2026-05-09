from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    from control_queue_db import connect, consume_next, stats, step_relative
except Exception:
    # Allow execution from alternate working directories during verification.
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from control_queue_db import connect, consume_next, stats, step_relative

VERSION = "v1.8D_operator_authority_resolver_reporting_complete"
SCHEMA = "rmu.effective_control_state.v1_8A"
DEFAULT_WEIGHTS = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0,
}
FIELD_RECIPES = {
    0: {"radial": 1.0, "orbital": 1.0, "vertical": 1.0, "turbulence": 1.0, "shell": 1.0},
    1: {"radial": 2.25, "orbital": 0.0, "vertical": 0.0, "turbulence": 0.0, "shell": 0.0},
    2: {"radial": 0.0, "orbital": 2.25, "vertical": 0.0, "turbulence": 0.0, "shell": 0.0},
    3: {"radial": 0.0, "orbital": 0.0, "vertical": 2.25, "turbulence": 0.0, "shell": 0.0},
    4: {"radial": 0.0, "orbital": 0.0, "vertical": 0.0, "turbulence": 2.25, "shell": 0.0},
    5: {"radial": 0.0, "orbital": 0.0, "vertical": 0.0, "turbulence": 0.0, "shell": 2.25},
    6: {"radial": 1.0, "orbital": 1.0, "vertical": 0.5, "turbulence": 0.6, "shell": 0.85},
    7: {"radial": 1.0, "orbital": 1.0, "vertical": 0.5, "turbulence": 1.75, "shell": 1.25},
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    tmp_path = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
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


def read_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    try:
        if not path.exists():
            return default
        data = json.loads(path.read_text())
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return default


def normalized_weights(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        value = {}
    return {name: safe_float(value.get(name), default) for name, default in DEFAULT_WEIGHTS.items()}


def default_state() -> Dict[str, Any]:
    return {
        "schema": "rmu.operator_authority_state.v1_8A",
        "version": "v1.8A",
        "auto_fields_enabled": False,
        "auto_behavior_enabled": False,
        "auto_camera_enabled": False,
        "no_behavior_enabled": True,
        "queues_paused": False,
        "behavior_queue_paused": False,
        "field_queue_paused": False,
        "active_auto_domain": "behavior",
        "behavior_step_seconds": 30.0,
        "field_step_seconds": 20.0,
        "manual_scene_index": 0,
        "manual_behavior_code": 0,
        "last_manual_behavior_code": 1,
        "selected_field_layer": "radial",
        "manual_field_weights": dict(DEFAULT_WEIGHTS),
        "dataset_coupling_mode": "observe",
        "vcv_event_recording_enabled": True,
        "vcv_continuous_enabled": True,
        "linked_behavior_presets_enabled": False,
        "linked_scene_presets_enabled": False,
        "last_behavior_event_id": 0,
        "last_field_event_id": 0,
        "last_behavior_step_unix": 0.0,
        "last_field_step_unix": 0.0,
        "command": {},
    }


def load_operator(path: Path) -> Dict[str, Any]:
    state = default_state()
    loaded = read_json(path, {})
    if isinstance(loaded, dict):
        state.update(loaded)

    state["manual_field_weights"] = normalized_weights(state.get("manual_field_weights"))

    # Normalize fields that the v1.8C sweep reads back.
    for key in [
        "auto_fields_enabled",
        "auto_behavior_enabled",
        "auto_camera_enabled",
        "no_behavior_enabled",
        "queues_paused",
        "behavior_queue_paused",
        "field_queue_paused",
        "vcv_event_recording_enabled",
        "vcv_continuous_enabled",
        "linked_behavior_presets_enabled",
        "linked_scene_presets_enabled",
    ]:
        state[key] = safe_bool(state.get(key), default_state().get(key, False))

    state["behavior_step_seconds"] = safe_float(state.get("behavior_step_seconds"), 30.0)
    state["field_step_seconds"] = safe_float(state.get("field_step_seconds"), 20.0)
    state["manual_scene_index"] = safe_int(state.get("manual_scene_index"), 0)
    state["manual_behavior_code"] = safe_int(state.get("manual_behavior_code"), 0)
    state["last_manual_behavior_code"] = safe_int(state.get("last_manual_behavior_code"), 1)
    state["last_behavior_event_id"] = safe_int(state.get("last_behavior_event_id"), 0)
    state["last_field_event_id"] = safe_int(state.get("last_field_event_id"), 0)
    state["last_behavior_step_unix"] = safe_float(state.get("last_behavior_step_unix"), 0.0)
    state["last_field_step_unix"] = safe_float(state.get("last_field_step_unix"), 0.0)

    if state.get("active_auto_domain") not in {"behavior", "field", "scene", "all"}:
        state["active_auto_domain"] = "behavior"
    if state.get("dataset_coupling_mode") not in {"off", "observe", "propose", "apply"}:
        state["dataset_coupling_mode"] = "observe"
    if state.get("selected_field_layer") not in DEFAULT_WEIGHTS:
        state["selected_field_layer"] = "radial"
    if not isinstance(state.get("command"), dict):
        state["command"] = {}

    return state


def save_operator(path: Path, state: Dict[str, Any]) -> None:
    state["updated_utc"] = utc_now_iso()
    atomic_write_json(path, state)


def handle_command(state: Dict[str, Any], conn: Any) -> Dict[str, Any]:
    cmd = state.get("command") if isinstance(state.get("command"), dict) else {}
    if not cmd or cmd.get("processed"):
        return state

    action = cmd.get("action", "")
    if action == "queue_step":
        domain = cmd.get("domain", state.get("active_auto_domain", "behavior"))
        if domain == "all":
            domain = "behavior"
        delta = safe_int(cmd.get("delta"), 1)
        current_id = safe_int(state.get(f"last_{domain}_event_id"), 0)
        row = step_relative(conn, domain, current_id, delta)
        if row:
            event_id = int(row[0])
            step_value = int(row[1])
            if domain == "behavior":
                state["manual_behavior_code"] = step_value
                state["no_behavior_enabled"] = step_value == 0
                state["last_manual_behavior_code"] = step_value or state.get("last_manual_behavior_code", 1)
                state["last_behavior_event_id"] = event_id
                state["auto_behavior_enabled"] = False
            elif domain == "field":
                state["manual_scene_index"] = step_value
                state["manual_field_weights"] = dict(FIELD_RECIPES.get(step_value, DEFAULT_WEIGHTS))
                state["last_field_event_id"] = event_id
                state["auto_fields_enabled"] = False

    elif action == "clear_queues":
        conn.execute("DELETE FROM events")
        conn.commit()
        state["last_behavior_event_id"] = 0
        state["last_field_event_id"] = 0

    state.setdefault("command", {})["processed"] = True
    state["command"]["processed_utc"] = utc_now_iso()
    return state


def resolve_once(root: Path, conn: Any) -> Dict[str, Any]:
    op_path = root / "output/operator_authority_state.json"
    eff_path = root / "output/effective_control_state.json"
    legacy_path = root / "output/manual_authority_mode.json"

    state = handle_command(load_operator(op_path), conn)
    now = time.time()

    behavior_step_seconds = safe_float(state.get("behavior_step_seconds"), 30.0)
    field_step_seconds = safe_float(state.get("field_step_seconds"), 20.0)

    if (
        state.get("auto_behavior_enabled")
        and not state.get("no_behavior_enabled")
        and not state.get("queues_paused")
        and not state.get("behavior_queue_paused")
        and now - safe_float(state.get("last_behavior_step_unix"), 0.0) >= behavior_step_seconds
    ):
        row = consume_next(conn, "behavior")
        if row:
            event_id = int(row[0])
            step_value = int(row[1])
            state["manual_behavior_code"] = step_value
            state["last_manual_behavior_code"] = step_value or state.get("last_manual_behavior_code", 1)
            state["last_behavior_event_id"] = event_id
            state["last_behavior_step_unix"] = now

    if (
        state.get("auto_fields_enabled")
        and not state.get("queues_paused")
        and not state.get("field_queue_paused")
        and now - safe_float(state.get("last_field_step_unix"), 0.0) >= field_step_seconds
    ):
        row = consume_next(conn, "field")
        if row:
            event_id = int(row[0])
            step_value = int(row[1])
            state["manual_scene_index"] = step_value
            state["manual_field_weights"] = dict(FIELD_RECIPES.get(step_value, DEFAULT_WEIGHTS))
            state["last_field_event_id"] = event_id
            state["last_field_step_unix"] = now

    behavior_code = 0 if state.get("no_behavior_enabled") else safe_int(state.get("manual_behavior_code"), 0)
    field_weights = normalized_weights(state.get("manual_field_weights"))
    scene_index = float(safe_int(state.get("manual_scene_index"), 0))
    qstats = stats(conn)

    modes = {
        "auto_fields_enabled": bool(state.get("auto_fields_enabled")),
        "auto_behavior_enabled": bool(state.get("auto_behavior_enabled")),
        "auto_camera_enabled": bool(state.get("auto_camera_enabled")),
        "no_behavior_enabled": bool(state.get("no_behavior_enabled")),
        "queues_paused": bool(state.get("queues_paused")),
        "behavior_queue_paused": bool(state.get("behavior_queue_paused")),
        "field_queue_paused": bool(state.get("field_queue_paused")),
        "active_auto_domain": state.get("active_auto_domain", "behavior"),
        "vcv_event_recording_enabled": bool(state.get("vcv_event_recording_enabled")),
        "vcv_continuous_enabled": bool(state.get("vcv_continuous_enabled")),
        # v1.8D reporting completion fields.
        "linked_behavior_presets_enabled": bool(state.get("linked_behavior_presets_enabled")),
        "linked_scene_presets_enabled": bool(state.get("linked_scene_presets_enabled")),
    }

    timing = {
        # v1.8D reports these always, including when queues are paused.
        "behavior_step_seconds": behavior_step_seconds,
        "field_step_seconds": field_step_seconds,
    }

    effective = {
        "schema": SCHEMA,
        "version": VERSION,
        "updated_utc": utc_now_iso(),
        "updated_by": "operator_authority_resolver.py",
        "authority": {
            "behavior": "hotkey_no_behavior" if state.get("no_behavior_enabled") else ("hotkey_auto_queue" if state.get("auto_behavior_enabled") else "hotkey_manual"),
            "field_weights": "hotkey_auto_queue" if state.get("auto_fields_enabled") else "hotkey_manual",
            "field_recipe": "hotkey_auto_queue" if state.get("auto_fields_enabled") else "hotkey_manual",
            "camera": "hotkey_auto" if state.get("auto_camera_enabled") else "hotkey_manual",
            "dataset_coupling": state.get("dataset_coupling_mode", "observe"),
            "vcv": "event_source_and_continuous_source",
        },
        "modes": modes,
        "timing": timing,
        "queue": qstats,
        "effective": {
            "scene_index": scene_index,
            "behavior_code": float(behavior_code),
            "behavior_authority_gate": 0.0,
            "field_weights": field_weights,
        },
        "operator_state_path": str(op_path),
    }

    save_operator(op_path, state)
    atomic_write_json(eff_path, effective)

    # Compatibility writer for older scripts that still inspect manual_authority_mode.json.
    legacy_state = dict(state)
    legacy_state.update(
        schema="rmu.manual_authority_mode.v1_8D_compat",
        version="v1.8D-operator-authority-compat",
        manual_behavior_code=behavior_code,
        manual_scene_index=int(scene_index),
        manual_field_weights=field_weights,
    )
    atomic_write_json(legacy_path, legacy_state)

    return effective


def main() -> int:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.8D operator authority resolver.")
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--interval", type=float, default=0.10)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    conn = connect(root / "output/control_events.sqlite")

    while True:
        effective = resolve_once(root, conn)
        if not args.quiet:
            print(
                "[v1.8D resolver] "
                f"behavior={effective['effective']['behavior_code']} "
                f"scene={effective['effective']['scene_index']} "
                f"timing={effective.get('timing')} "
                f"linked=({effective.get('modes', {}).get('linked_behavior_presets_enabled')},"
                f"{effective.get('modes', {}).get('linked_scene_presets_enabled')})",
                flush=True,
            )
        if args.once:
            return 0
        time.sleep(max(0.05, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
