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
#   field snapping, behavior rapid switching, and camera changes.
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
    source: str = "manual_authority_lock",
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
        "stabilized_by": PATCH_VERSION,
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
        data.get("values"),
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
            "shell": 1.0,
        },
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
            "/ch/8": {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0},
            "/ch/18": {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0},
            "/ch/19": {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0},
        },
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
    fallback: int,
) -> int:
    current_ms = now_ms()
    channels = lock_state.setdefault("channels", {})
    state = channels.setdefault(
        channel,
        {"stable": fallback, "candidate": fallback, "candidate_since_ms": current_ms, "last_change_ms": 0},
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
    off_threshold: float,
) -> int:
    current_ms = now_ms()
    channels = lock_state.setdefault("channels", {})
    state = channels.setdefault(
        channel,
        {"stable": 0, "candidate": 0, "candidate_since_ms": current_ms, "last_change_ms": 0},
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
    vcv_data: Dict[str, Any],
    config: Dict[str, Any],
    mode: Dict[str, Any],
    lock_state: Dict[str, Any],
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
            fallback=safe_int(mode.get("manual_scene_index"), 0),
        )

        set_channel_value(data, "/ch/8", "scene_index", float(scene), raw_value=raw_scene, locked=False, source="slow_auto_fields")
        field_source = "slow_auto_fields"
        scene_source = "slow_auto_fields"

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
            fallback=safe_int(mode.get("manual_behavior_code"), 0),
        )

        raw_gate = get_channel_raw(data, "/ch/19", "behavior_authority_gate", 0.0)

        gate_state = slow_latch_gate(
            lock_state=lock_state,
            channel="/ch/19",
            raw_voltage=raw_gate,
            hold_ms=safe_int(timing.get("gate_hold_ms"), 10000),
            on_threshold=safe_float(timing.get("gate_on_threshold"), 6.0),
            off_threshold=safe_float(timing.get("gate_off_threshold"), 4.0),
        )

        gate_voltage = 10.0 if gate_state else 0.0

        set_channel_value(data, "/ch/18", "behavior_code", float(behavior), raw_value=raw_behavior, locked=False, source="slow_auto_behavior")
        set_channel_value(data, "/ch/19", "behavior_authority_gate", gate_voltage, raw_value=raw_gate, locked=False, source="slow_auto_behavior_gate")

        behavior_source = "slow_auto_behavior"
        gate_source = "slow_auto_behavior_gate"

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
            "behavior_may_not_switch_camera": False,
            "scene_may_not_switch_camera": False,
            "behavior_may_not_switch_camera_note": "False here means behavior is not permitted to switch camera.",
            "scene_may_not_switch_camera_note": "False here means scene is not permitted to switch camera."
        },
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
        "auto_camera_enabled": auto_camera,
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
            "shell": safe_float(data["mapped_values"].get("shell"), 1.0),
        },
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
                vcv_data=vcv_data,
                config=config,
                mode=mode,
                lock_state=lock_state,
            )

            atomic_write_json(locked_path, locked_data)
            atomic_write_json(state_path, lock_state)

            # Hard write-back for current renderer compatibility.
            atomic_write_json(vcv_path, locked_data)

            eff = lock_state.get("effective", {})
            mode_summary = lock_state.get("mode", {})

            log_path.parent.mkdir(parents=True, exist_ok=True)
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
                log_path.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("--root", default=os.environ.get("RMU_ROOT", os.getcwd()), help="RealMathUniverse project root.")
    parser.add_argument("--interval", type=float, default=0.02, help="Loop interval in seconds. Default is 0.02 for hard lock enforcement.")
    parser.add_argument("--once", action="store_true", help="Run once and exit.")
    parser.add_argument("--quiet", action="store_true", help="Reduce console output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()

    return run_lock(
        root=root,
        interval=max(0.01, float(args.interval)),
        once=bool(args.once),
        quiet=bool(args.quiet),
    )


if __name__ == "__main__":
    raise SystemExit(main())
