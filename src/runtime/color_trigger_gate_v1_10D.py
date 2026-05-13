from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


VERSION = "v1.10D_color_trigger_gate"
SCHEMA = "rmu.color_override_state.v1_10D"

DEFAULT_COLOR_NAMES = {
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
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
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


def read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        obj = json.loads(path.read_text())
        return obj
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


def channel_value(vcv: Dict[str, Any], channel: str) -> Optional[float]:
    for section_name in ("channels", "direct_channels", "raw_channels"):
        section = vcv.get(section_name)
        if isinstance(section, dict):
            entry = section.get(channel)
            if isinstance(entry, dict):
                return safe_float(entry.get("value", entry.get("raw")), 0.0)
            if entry is not None:
                return safe_float(entry, 0.0)
    return None


def load_schema(root: Path) -> Dict[str, Any]:
    schema_path = root / "config/color_step_schema_v1_10D.json"
    schema = read_json(schema_path, {})
    if not isinstance(schema, dict) or "steps" not in schema:
        return {
            "input_channel": "/ch/7",
            "trigger_channel": "/ch/19",
            "trigger_high_threshold": 5.0,
            "trigger_rearm_threshold": 2.0,
            "steps": [
                {"slot": 0, "voltage": 0.00, "color_mode": 1, "name": "species_family"},
                {"slot": 1, "voltage": 1.43, "color_mode": 2, "name": "depth_temperature"},
                {"slot": 2, "voltage": 2.86, "color_mode": 3, "name": "field_energy"},
                {"slot": 3, "voltage": 4.29, "color_mode": 4, "name": "curvature_density"},
                {"slot": 4, "voltage": 5.71, "color_mode": 5, "name": "higgs_lambda"},
                {"slot": 5, "voltage": 7.14, "color_mode": 6, "name": "probability_weight"},
                {"slot": 6, "voltage": 8.57, "color_mode": 9, "name": "pioneer_green"},
                {"slot": 7, "voltage": 10.00, "color_mode": 10, "name": "amber_scope"},
            ],
        }
    return schema


def nearest_step(voltage: float, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not steps:
        return {"slot": 0, "voltage": 0.0, "color_mode": 1, "name": "species_family"}
    return min(steps, key=lambda step: abs(safe_float(step.get("voltage"), 0.0) - voltage))


def read_existing_color(root: Path) -> Dict[str, Any]:
    existing = read_json(root / "output/color_override_state.json", {})
    return existing if isinstance(existing, dict) else {}


def write_color(root: Path, payload: Dict[str, Any]) -> None:
    for name in (
        "output/color_override_state.json",
        "output/hud_color_state.json",
        "output/color_control_state.json",
    ):
        atomic_write_json(root / name, payload)


def update_operator_color(root: Path, mode: int, source: str) -> None:
    path = root / "output/operator_authority_state.json"
    op = read_json(path, {})
    if not isinstance(op, dict):
        op = {}

    op["color_mode"] = mode
    op["manual_color_mode"] = mode if source == "manual_gate_low" else op.get("manual_color_mode", mode)
    op["vcv_color_auto_enabled"] = source == "vcv_ch19_trigger_ch7_sample"
    op["color_authority"] = source
    op["updated_by"] = VERSION
    op["updated_unix"] = time.time()
    op["updated_utc"] = utc_now_iso()

    atomic_write_json(path, op)


def build_payload(
    mode: int,
    name: str,
    source: str,
    ch7_voltage: Optional[float],
    ch19_voltage: Optional[float],
    sampled: bool,
    armed: bool,
    slot: Optional[int],
) -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "updated_utc": utc_now_iso(),
        "updated_unix": time.time(),
        "updated_by": VERSION,
        "color_mode": int(mode),
        "color_name": name,
        "source": source,
        "authority": source,
        "input_channel": "/ch/7",
        "trigger_channel": "/ch/19",
        "color_voltage": ch7_voltage,
        "trigger_voltage": ch19_voltage,
        "trigger_sampled_this_tick": sampled,
        "trigger_armed": armed,
        "sampled_slot": slot,
        "manual_when_gate_low": True,
        "note": "/ch/7 is color voltage. /ch/19 samples/authorizes color. /ch/8 is untouched."
    }


def tick(root: Path, armed: bool) -> bool:
    schema = load_schema(root)
    steps = schema.get("steps", [])
    high = safe_float(schema.get("trigger_high_threshold"), 5.0)
    low = safe_float(schema.get("trigger_rearm_threshold"), 2.0)

    vcv = read_json(root / "output/vcv_state.json", {})
    if not isinstance(vcv, dict):
        vcv = {}

    ch7 = channel_value(vcv, "/ch/7")
    ch19 = channel_value(vcv, "/ch/19")

    existing = read_existing_color(root)
    current_mode = safe_int(existing.get("color_mode"), 1)
    current_name = str(existing.get("color_name", DEFAULT_COLOR_NAMES.get(current_mode, "unknown")))

    sampled = False
    source = str(existing.get("source", "manual_gate_low"))
    slot = existing.get("sampled_slot")

    if ch19 is not None and ch19 <= low:
        armed = True
        source = "manual_gate_low"

    if ch19 is not None and ch19 >= high and armed and ch7 is not None:
        step = nearest_step(ch7, steps)
        current_mode = safe_int(step.get("color_mode"), 1)
        current_name = str(step.get("name", DEFAULT_COLOR_NAMES.get(current_mode, "unknown")))
        slot = safe_int(step.get("slot"), 0)
        source = "vcv_ch19_trigger_ch7_sample"
        sampled = True
        armed = False

    payload = build_payload(
        mode=current_mode,
        name=current_name,
        source=source,
        ch7_voltage=ch7,
        ch19_voltage=ch19,
        sampled=sampled,
        armed=armed,
        slot=safe_int(slot, 0) if slot is not None else None,
    )

    write_color(root, payload)
    update_operator_color(root, current_mode, source)

    return armed


def main() -> int:
    parser = argparse.ArgumentParser(description="RMU v1.10D /ch7 color voltage + /ch19 trigger/gate service.")
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--interval", type=float, default=0.05)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    armed = True

    while True:
        armed = tick(root, armed)

        if args.once:
            payload = read_existing_color(root)
            if not args.quiet:
                print(json.dumps(payload, indent=2))
            return 0

        if not args.quiet:
            payload = read_existing_color(root)
            print(
                f"[{VERSION}] color={payload.get('color_mode')} {payload.get('color_name')} "
                f"src={payload.get('source')} ch7={payload.get('color_voltage')} "
                f"ch19={payload.get('trigger_voltage')} armed={payload.get('trigger_armed')}",
                flush=True,
            )

        time.sleep(max(0.01, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
