from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


try:
    from control_queue_db import connect, consume_next, stats, step_relative
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from control_queue_db import connect, consume_next, stats, step_relative


VERSION = "v1.10D_ch8_behavior_gate_ch18_behavior_voltage"
SCHEMA = "rmu.effective_control_state.v1_10D"


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


COLOR_NAMES = {
    0: "white_cluster",
    1: "species_family",
    2: "depth_temperature",
    3: "field_energy",
    4: "curvature_density",
    5: "higgs_lambda",
    6: "probability_weight",
    7: "vcv_color_bank",
    8: "sonar_heat",
    9: "pioneer_green",
    10: "amber_scope",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(str(tmp_path), str(path))

    finally:
        if tmp_path.exists():
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
        return data

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
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled", "apply"}

    return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def voltage_to_behavior(volts: float) -> int:
    """
    /ch/18 behavior voltage:
      0V  -> behavior 0
      10V -> behavior 7
    """
    return int(clamp(round((clamp(volts, 0.0, 10.0) / 10.0) * 7.0), 0, 7))


def voltage_to_color_11_step(volts: float) -> int:
    """
    /ch/7 color voltage:
      0V  -> color 0
      10V -> color 10
    """
    return int(clamp(round(clamp(volts, 0.0, 10.0)), 0, 10))


def normalized_weights(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        value = {}

    return {
        name: safe_float(value.get(name), default)
        for name, default in DEFAULT_WEIGHTS.items()
    }


def channel_value(vcv: Dict[str, Any], channel: str) -> Optional[float]:
    """
    Read a channel from bridge-owned VCV truth.
    This resolver must never fabricate values inside vcv_state.json.
    """
    if not isinstance(vcv, dict):
        return None

    for section_name in ("channels", "direct_channels", "raw_channels"):
        section = vcv.get(section_name)

        if isinstance(section, dict):
            entry = section.get(channel)

            if isinstance(entry, dict):
                return safe_float(entry.get("value", entry.get("raw")), 0.0)

            if entry is not None:
                return safe_float(entry, 0.0)

    return None


def default_operator_state() -> Dict[str, Any]:
    return {
        "schema": "rmu.operator_authority_state.v1_10D",
        "version": "v1.10D",

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

        "manual_color_mode": 1,
        "color_mode": 1,

        "vcv_behavior_auto_enabled": False,
        "vcv_color_auto_enabled": False,

        "vcv_event_recording_enabled": True,
        "vcv_continuous_enabled": True,

        "linked_behavior_presets_enabled": False,
        "linked_scene_presets_enabled": False,

        "last_behavior_event_id": 0,
        "last_field_event_id": 0,

        "last_behavior_step_unix": 0.0,
        "last_field_step_unix": 0.0,

        "last_hotkey": None,
        "last_hotkey_reason": None,

        "command": {},
    }


def load_operator_state(path: Path) -> Dict[str, Any]:
    state = default_operator_state()
    loaded = read_json(path, {})

    if isinstance(loaded, dict):
        state.update(loaded)

    state["manual_field_weights"] = normalized_weights(state.get("manual_field_weights"))

    bool_keys = [
        "auto_fields_enabled",
        "auto_behavior_enabled",
        "auto_camera_enabled",
        "no_behavior_enabled",
        "queues_paused",
        "behavior_queue_paused",
        "field_queue_paused",
        "vcv_behavior_auto_enabled",
        "vcv_color_auto_enabled",
        "vcv_event_recording_enabled",
        "vcv_continuous_enabled",
        "linked_behavior_presets_enabled",
        "linked_scene_presets_enabled",
    ]

    defaults = default_operator_state()

    for key in bool_keys:
        state[key] = safe_bool(state.get(key), safe_bool(defaults.get(key), False))

    int_keys = [
        "manual_scene_index",
        "manual_behavior_code",
        "last_manual_behavior_code",
        "manual_color_mode",
        "color_mode",
        "last_behavior_event_id",
        "last_field_event_id",
    ]

    for key in int_keys:
        state[key] = safe_int(state.get(key), safe_int(defaults.get(key), 0))

    state["manual_color_mode"] = int(clamp(state["manual_color_mode"], 0, 10))
    state["color_mode"] = int(clamp(state["color_mode"], 0, 10))

    state["behavior_step_seconds"] = safe_float(state.get("behavior_step_seconds"), 30.0)
    state["field_step_seconds"] = safe_float(state.get("field_step_seconds"), 20.0)

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


def save_operator_state(path: Path, state: Dict[str, Any]) -> None:
    state["updated_utc"] = utc_now_iso()
    state["updated_unix"] = time.time()
    atomic_write_json(path, state)


def handle_command(state: Dict[str, Any], conn: Any) -> Dict[str, Any]:
    cmd = state.get("command") if isinstance(state.get("command"), dict) else {}

    if not cmd or cmd.get("processed"):
        return state

    action = str(cmd.get("action", ""))

    if action == "queue_step":
        domain = str(cmd.get("domain", state.get("active_auto_domain", "behavior")))

        if domain == "all":
            domain = "behavior"

        delta = safe_int(cmd.get("delta"), 1)
        current_id = safe_int(state.get(f"last_{domain}_event_id"), 0)

        row = step_relative(conn, domain, current_id, delta)

        if row:
            event_id = int(row[0])
            step_value = int(row[1])

            if domain == "behavior":
                state["manual_behavior_code"] = int(clamp(step_value, 0, 7))
                state["no_behavior_enabled"] = state["manual_behavior_code"] == 0
                state["last_manual_behavior_code"] = state["manual_behavior_code"] or state.get("last_manual_behavior_code", 1)
                state["last_behavior_event_id"] = event_id
                state["auto_behavior_enabled"] = False
                state["vcv_behavior_auto_enabled"] = False

            elif domain == "field":
                state["manual_scene_index"] = int(clamp(step_value, 0, 7))
                state["manual_field_weights"] = dict(FIELD_RECIPES.get(state["manual_scene_index"], DEFAULT_WEIGHTS))
                state["last_field_event_id"] = event_id
                state["auto_fields_enabled"] = False

    elif action == "clear_queues":
        conn.execute("DELETE FROM events")
        conn.commit()
        state["last_behavior_event_id"] = 0
        state["last_field_event_id"] = 0

    elif action == "set_behavior":
        code = int(clamp(safe_int(cmd.get("code"), 0), 0, 7))
        state["manual_behavior_code"] = code
        state["last_manual_behavior_code"] = code or state.get("last_manual_behavior_code", 1)
        state["no_behavior_enabled"] = code == 0
        state["auto_behavior_enabled"] = False
        state["vcv_behavior_auto_enabled"] = False

    elif action == "set_color":
        mode = int(clamp(safe_int(cmd.get("mode"), state.get("manual_color_mode", 1)), 0, 10))
        state["manual_color_mode"] = mode
        state["color_mode"] = mode
        state["vcv_color_auto_enabled"] = False

    state["command"]["processed"] = True
    state["command"]["processed_utc"] = utc_now_iso()

    return state


def write_color_state(
    root: Path,
    mode: int,
    source: str,
    ch7_voltage: Optional[float],
    ch19_gate: Optional[float],
) -> Dict[str, Any]:
    mode = int(clamp(mode, 0, 10))

    payload = {
        "schema": "rmu.color_override_state.v1_10D",
        "version": VERSION,
        "updated_utc": utc_now_iso(),
        "updated_unix": time.time(),
        "updated_by": "operator_authority_resolver.py",

        "color_mode": mode,
        "color_name": COLOR_NAMES.get(mode, "unknown"),

        "source": source,
        "authority": source,

        "color_channel": "/ch/7",
        "color_voltage": ch7_voltage,

        "gate_channel": "/ch/19",
        "gate_voltage": ch19_gate,

        "manual_when_gate_low": True,

        "note": "/ch/7 is color voltage. /ch/19 is color gate/trigger. /ch/8 is behavior gate only.",
    }

    atomic_write_json(root / "output/color_override_state.json", payload)
    atomic_write_json(root / "output/hud_color_state.json", payload)
    atomic_write_json(root / "output/color_control_state.json", payload)

    return payload


def resolve_behavior(state: Dict[str, Any], vcv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final behavior authority rule:

      /ch/8  = behavior trigger/gate
      /ch/18 = behavior mode voltage
      /ch/19 is never behavior
      /ch/7 is never behavior

    Manual override rule:
      SHIFT+0 through SHIFT+7 should write manual_behavior_code and set
      auto_behavior_enabled false. This resolver honors that state.
    """
    behavior_code = 0 if state.get("no_behavior_enabled") else safe_int(state.get("manual_behavior_code"), 0)
    behavior_gate = 0.0
    behavior_source = "hotkey_no_behavior" if state.get("no_behavior_enabled") else "hotkey_manual"

    ch8_gate = channel_value(vcv, "/ch/8")
    ch18_voltage = channel_value(vcv, "/ch/18")

    if state.get("auto_behavior_enabled") and not state.get("no_behavior_enabled"):
        if ch8_gate is not None and ch8_gate >= 5.0 and ch18_voltage is not None:
            behavior_code = voltage_to_behavior(ch18_voltage)
            behavior_gate = ch8_gate
            behavior_source = "vcv_ch8_gate_ch18_behavior"
            state["manual_behavior_code"] = behavior_code
            state["last_manual_behavior_code"] = behavior_code or state.get("last_manual_behavior_code", 1)
            state["vcv_behavior_auto_enabled"] = True
        else:
            behavior_code = safe_int(state.get("manual_behavior_code"), 0)
            behavior_gate = safe_float(ch8_gate, 0.0)
            behavior_source = "manual_ch8_gate_low"
            state["vcv_behavior_auto_enabled"] = False

    return {
        "behavior_code": int(clamp(behavior_code, 0, 7)),
        "behavior_gate": behavior_gate,
        "behavior_source": behavior_source,
        "ch8_gate": ch8_gate,
        "ch18_voltage": ch18_voltage,
    }


def resolve_color(root: Path, state: Dict[str, Any], vcv: Dict[str, Any]) -> Dict[str, Any]:
    """
    Color rule:

      /ch/7  = color voltage
      /ch/19 = color gate/trigger
      /ch/8 is untouched by color

    If /ch/19 >= 5V, color follows /ch/7.
    If /ch/19 < 5V, manual_color_mode holds.
    """
    ch7_voltage = channel_value(vcv, "/ch/7")
    ch19_gate = channel_value(vcv, "/ch/19")

    manual_mode = int(clamp(safe_int(state.get("manual_color_mode", state.get("color_mode", 1)), 1), 0, 10))

    if ch19_gate is not None and ch19_gate >= 5.0 and ch7_voltage is not None:
        mode = voltage_to_color_11_step(ch7_voltage)
        source = "vcv_ch19_gate_ch7_color"
        state["vcv_color_auto_enabled"] = True
        state["color_mode"] = mode
    else:
        mode = manual_mode
        source = "manual_color_gate_low"
        state["vcv_color_auto_enabled"] = False
        state["color_mode"] = mode

    color_state = write_color_state(
        root=root,
        mode=mode,
        source=source,
        ch7_voltage=ch7_voltage,
        ch19_gate=ch19_gate,
    )

    return {
        "color_mode": mode,
        "color_name": COLOR_NAMES.get(mode, "unknown"),
        "color_source": source,
        "color_gate": safe_float(ch19_gate, 0.0),
        "ch7_voltage": ch7_voltage,
        "ch19_gate": ch19_gate,
        "color_state": color_state,
    }


def resolve_fields(state: Dict[str, Any], dataset_coupling: Dict[str, Any]) -> Dict[str, Any]:
    field_weights = normalized_weights(state.get("manual_field_weights"))
    field_source = "hotkey_auto_queue" if state.get("auto_fields_enabled") else "hotkey_manual"

    coupling_mode = str(state.get("dataset_coupling_mode", "observe"))
    coupling_weights = dataset_coupling.get("field_targets") or dataset_coupling.get("field_weights")

    if coupling_mode == "apply" and isinstance(coupling_weights, dict):
        field_weights = normalized_weights(coupling_weights)
        field_source = "dataset_coupling_apply"

    return {
        "field_weights": field_weights,
        "field_source": field_source,
    }


def process_auto_queues(state: Dict[str, Any], conn: Any, now: float) -> Dict[str, Any]:
    if (
        state.get("auto_behavior_enabled")
        and not state.get("no_behavior_enabled")
        and not state.get("queues_paused")
        and not state.get("behavior_queue_paused")
        and now - safe_float(state.get("last_behavior_step_unix"), 0.0) >= safe_float(state.get("behavior_step_seconds"), 30.0)
    ):
        row = consume_next(conn, "behavior")

        if row:
            event_id = int(row[0])
            step_value = int(row[1])

            state["manual_behavior_code"] = int(clamp(step_value, 0, 7))
            state["last_manual_behavior_code"] = state["manual_behavior_code"] or state.get("last_manual_behavior_code", 1)
            state["last_behavior_event_id"] = event_id
            state["last_behavior_step_unix"] = now

    if (
        state.get("auto_fields_enabled")
        and not state.get("queues_paused")
        and not state.get("field_queue_paused")
        and now - safe_float(state.get("last_field_step_unix"), 0.0) >= safe_float(state.get("field_step_seconds"), 20.0)
    ):
        row = consume_next(conn, "field")

        if row:
            event_id = int(row[0])
            step_value = int(row[1])

            state["manual_scene_index"] = int(clamp(step_value, 0, 7))
            state["manual_field_weights"] = dict(FIELD_RECIPES.get(state["manual_scene_index"], DEFAULT_WEIGHTS))
            state["last_field_event_id"] = event_id
            state["last_field_step_unix"] = now

    return state


def resolve_once(root: Path, conn: Any) -> Dict[str, Any]:
    op_path = root / "output/operator_authority_state.json"
    eff_path = root / "output/effective_control_state.json"
    manual_path = root / "output/manual_authority_mode.json"

    now = time.time()

    state = load_operator_state(op_path)
    state = handle_command(state, conn)
    state = process_auto_queues(state, conn, now)

    vcv = read_json(root / "output/vcv_state.json", {})
    if not isinstance(vcv, dict):
        vcv = {}

    dataset_coupling = read_json(root / "output/dataset_coupling_state.json", {})
    if not isinstance(dataset_coupling, dict):
        dataset_coupling = {}

    behavior = resolve_behavior(state, vcv)
    color = resolve_color(root, state, vcv)
    fields = resolve_fields(state, dataset_coupling)

    scene_index = float(safe_int(state.get("manual_scene_index"), 0))

    coupling_mode = str(state.get("dataset_coupling_mode", "observe"))
    coupling_loaded = safe_bool(dataset_coupling.get("loaded"), False)
    coupling_fallback = safe_bool(dataset_coupling.get("fallback"), False)

    try:
        queue_stats = stats(conn)
    except Exception:
        queue_stats = {}

    effective = {
        "schema": SCHEMA,
        "version": VERSION,
        "updated_utc": utc_now_iso(),
        "updated_unix": now,
        "updated_by": "operator_authority_resolver.py",

        "authority": {
            "behavior": behavior["behavior_source"],
            "field_weights": fields["field_source"],
            "field_recipe": fields["field_source"],
            "camera": "hotkey_auto" if state.get("auto_camera_enabled") else "hotkey_manual",
            "dataset_coupling": coupling_mode,
            "color": color["color_source"],
            "vcv": "pure_vcv_signal_truth",
        },

        "modes": {
            "auto_fields_enabled": bool(state.get("auto_fields_enabled")),
            "auto_behavior_enabled": bool(state.get("auto_behavior_enabled")),
            "auto_camera_enabled": bool(state.get("auto_camera_enabled")),
            "no_behavior_enabled": bool(state.get("no_behavior_enabled")),
            "queues_paused": bool(state.get("queues_paused")),
            "behavior_queue_paused": bool(state.get("behavior_queue_paused")),
            "field_queue_paused": bool(state.get("field_queue_paused")),
            "active_auto_domain": state.get("active_auto_domain", "behavior"),
            "vcv_behavior_auto_enabled": bool(state.get("vcv_behavior_auto_enabled")),
            "vcv_color_auto_enabled": bool(state.get("vcv_color_auto_enabled")),
            "vcv_event_recording_enabled": bool(state.get("vcv_event_recording_enabled")),
            "vcv_continuous_enabled": bool(state.get("vcv_continuous_enabled")),
            "linked_behavior_presets_enabled": bool(state.get("linked_behavior_presets_enabled")),
            "linked_scene_presets_enabled": bool(state.get("linked_scene_presets_enabled")),
        },

        "timing": {
            "behavior_step_seconds": safe_float(state.get("behavior_step_seconds"), 30.0),
            "field_step_seconds": safe_float(state.get("field_step_seconds"), 20.0),
        },

        "queue": queue_stats,

        "effective": {
            "scene_index": scene_index,
            "behavior_code": float(behavior["behavior_code"]),
            "behavior_authority_gate": float(behavior["behavior_gate"]),
            "field_weights": fields["field_weights"],
            "color_mode": int(color["color_mode"]),
            "color_name": color["color_name"],
            "color_gate": float(color["color_gate"]),
        },

        "behavior": {
            "code": int(behavior["behavior_code"]),
            "source": behavior["behavior_source"],
            "gate_channel": "/ch/8",
            "gate_voltage": behavior["ch8_gate"],
            "behavior_channel": "/ch/18",
            "behavior_voltage": behavior["ch18_voltage"],
        },

        "color": {
            "mode": int(color["color_mode"]),
            "name": color["color_name"],
            "source": color["color_source"],
            "color_channel": "/ch/7",
            "color_voltage": color["ch7_voltage"],
            "gate_channel": "/ch/19",
            "gate_voltage": color["ch19_gate"],
        },

        "dataset_coupling_mode": coupling_mode,
        "dataset_loaded": coupling_loaded,
        "fallback": coupling_fallback,
        "field_weights": fields["field_weights"],
        "field_targets": fields["field_weights"] if coupling_mode == "apply" else None,
        "dataset_drive": dataset_coupling.get("drive"),

        "operator_state_path": str(op_path),
    }

    state["manual_behavior_code"] = int(behavior["behavior_code"])
    state["color_mode"] = int(color["color_mode"])
    if not state.get("vcv_color_auto_enabled"):
        state["manual_color_mode"] = int(color["color_mode"])

    save_operator_state(op_path, state)
    atomic_write_json(eff_path, effective)

    legacy_state = dict(state)
    legacy_state.update(
        {
            "schema": "rmu.manual_authority_mode.v1_10D_compat",
            "version": "v1.10D-single-authority-compat",
            "manual_behavior_code": int(behavior["behavior_code"]),
            "manual_scene_index": int(scene_index),
            "manual_field_weights": fields["field_weights"],
            "color_mode": int(color["color_mode"]),
            "manual_color_mode": int(state.get("manual_color_mode", color["color_mode"])),
        }
    )
    atomic_write_json(manual_path, legacy_state)

    return effective


def main() -> int:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.10D single authority resolver.")
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
                "[v1.10D resolver] "
                f"behavior={effective['effective']['behavior_code']} "
                f"behavior_auth={effective['authority']['behavior']} "
                f"behavior_gate={effective['effective']['behavior_authority_gate']} "
                f"color={effective['effective']['color_mode']} "
                f"color_auth={effective['authority']['color']} "
                f"color_gate={effective['effective']['color_gate']} "
                f"fields={effective['authority']['field_weights']} "
                f"coupling={effective.get('dataset_coupling_mode')}",
                flush=True,
            )

        if args.once:
            return 0

        time.sleep(max(0.05, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
