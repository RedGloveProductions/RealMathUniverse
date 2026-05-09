#!/usr/bin/env python3
"""
RealMathUniverse v1.7F Hard Manual Authority Guard

This is deliberately aggressive. It continuously clamps the authority channels
that were causing field snapping and behavior machine-gunning, regardless of
what the VCV bridge writes. It preserves all other VCV channel data.

Locked in manual mode by default:
  /ch/2   radial
  /ch/3   orbital
  /ch/4   vertical
  /ch/5   turbulence
  /ch/6   shell
  /ch/8   scene_index
  /ch/18  behavior_code
  /ch/19  behavior_authority_gate

Auto mode can be enabled through output/hard_manual_authority_mode.json, but
manual remains the default and camera remains manual by default.
"""
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

VERSION = "v1.7F-hard-manual-authority-guard"

CHANNELS = {
    "/ch/2": "radial",
    "/ch/3": "orbital",
    "/ch/4": "vertical",
    "/ch/5": "turbulence",
    "/ch/6": "shell",
    "/ch/8": "scene_index",
    "/ch/18": "behavior_code",
    "/ch/19": "behavior_authority_gate",
}

FIELD_CHANNELS = {
    "/ch/2": "radial",
    "/ch/3": "orbital",
    "/ch/4": "vertical",
    "/ch/5": "turbulence",
    "/ch/6": "shell",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_ms() -> int:
    return int(time.monotonic() * 1000)


def sf(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def si(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    tmp_path: Optional[Path] = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
        tmp_path = Path(tmp)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = -1
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    finally:
        if fd != -1:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def read_json(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    try:
        if not path.exists():
            return {}, f"missing {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}, f"root was {type(data).__name__}, expected object"
        return data, None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def default_mode() -> Dict[str, Any]:
    return {
        "schema": "rmu.hard_manual_authority_mode.v1",
        "version": VERSION,
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
    data, err = read_json(path)
    if err:
        data = default_mode()
        atomic_write(path, data)
        return data
    base = default_mode()
    base.update(data)
    if not isinstance(base.get("manual_field_weights"), dict):
        base["manual_field_weights"] = default_mode()["manual_field_weights"]
    return base


def default_guard_state() -> Dict[str, Any]:
    t = now_ms()
    return {
        "schema": "rmu.hard_manual_authority_guard_state.v1",
        "version": VERSION,
        "created_utc": utc(),
        "channels": {
            "/ch/8": {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0},
            "/ch/18": {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0},
            "/ch/19": {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0},
        },
        "write_count": 0,
    }


def load_guard_state(path: Path) -> Dict[str, Any]:
    data, err = read_json(path)
    if err or not isinstance(data.get("channels"), dict):
        return default_guard_state()
    return data


def ensure_shape(data: Dict[str, Any]) -> None:
    for key in ["channels", "direct_channels", "mapped_values", "labels"]:
        if not isinstance(data.get(key), dict):
            data[key] = {}


def normalize_channel_key(value: Any) -> Optional[str]:
    text = str(value).strip() if value is not None else ""
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


def get_channel_value(data: Dict[str, Any], ch: str, label: str, default: float = 0.0) -> float:
    for container_name in ["channels", "direct_channels", "raw_channels", "values"]:
        container = data.get(container_name)
        if isinstance(container, dict):
            for k, entry in container.items():
                if normalize_channel_key(k) != ch:
                    continue
                if isinstance(entry, dict):
                    for field in ["raw", "mapped", "value", "stable"]:
                        if field in entry:
                            v = entry[field]
                            if isinstance(v, list) and v:
                                return sf(v[0], default)
                            return sf(v, default)
                else:
                    return sf(entry, default)
    mapped = data.get("mapped_values")
    if isinstance(mapped, dict) and label in mapped:
        return sf(mapped[label], default)
    if label in data:
        return sf(data[label], default)
    return default


def set_channel(data: Dict[str, Any], ch: str, label: str, value: float, raw: Optional[float] = None, locked: bool = True, source: str = "hard_manual_guard") -> None:
    ensure_shape(data)
    if raw is None:
        raw = value
    entry = {
        "label": label,
        "raw": raw,
        "mapped": value,
        "value": value,
        "stable": value,
        "locked": locked,
        "source": source,
        "stabilized": True,
        "stabilized_by": VERSION,
    }
    data["channels"][ch] = copy.deepcopy(entry)
    data["direct_channels"][ch] = copy.deepcopy(entry)
    data["mapped_values"][label] = value
    data["labels"][ch] = label
    data[label] = value
    data[ch.replace("/ch/", "ch")] = copy.deepcopy(entry)


def voltage_to_step(v: float, max_step: int = 7) -> int:
    if 0.0 <= v <= max_step and abs(v - round(v)) < 0.001:
        return int(clamp(round(v), 0, max_step))
    return int(round(clamp(v / 10.0, 0.0, 1.0) * max_step))


def slow_latch(state: Dict[str, Any], ch: str, candidate: int, hold_ms: int, interval_ms: int, fallback: int) -> int:
    t = now_ms()
    channels = state.setdefault("channels", {})
    st = channels.setdefault(ch, {"stable": fallback, "candidate": fallback, "candidate_since_ms": t, "last_change_ms": 0})
    stable = si(st.get("stable"), fallback)
    old = si(st.get("candidate"), fallback)
    since = si(st.get("candidate_since_ms"), t)
    last = si(st.get("last_change_ms"), 0)
    if candidate != old:
        st["candidate"] = candidate
        st["candidate_since_ms"] = t
        st["candidate_age_ms"] = 0
        st["accepted_change"] = False
        return stable
    cand_age = t - since
    change_age = t - last if last else 999999999
    if candidate != stable and cand_age >= hold_ms and change_age >= interval_ms:
        stable = candidate
        st["stable"] = stable
        st["last_change_ms"] = t
        st["accepted_change"] = True
    else:
        st["accepted_change"] = False
    st["candidate_age_ms"] = cand_age
    st["change_age_ms"] = change_age
    st["last_seen_ms"] = t
    return stable


def slow_gate(state: Dict[str, Any], ch: str, raw: float, hold_ms: int, on: float, off: float) -> int:
    t = now_ms()
    channels = state.setdefault("channels", {})
    st = channels.setdefault(ch, {"stable": 0, "candidate": 0, "candidate_since_ms": t, "last_change_ms": 0})
    stable = si(st.get("stable"), 0)
    candidate = 0 if stable and raw <= off else 1 if (not stable and raw >= on) else stable
    old = si(st.get("candidate"), 0)
    since = si(st.get("candidate_since_ms"), t)
    if candidate != old:
        st["candidate"] = candidate
        st["candidate_since_ms"] = t
        st["candidate_age_ms"] = 0
        st["accepted_change"] = False
        return stable
    cand_age = t - since
    if candidate != stable and cand_age >= hold_ms:
        stable = candidate
        st["stable"] = stable
        st["last_change_ms"] = t
        st["accepted_change"] = True
    else:
        st["accepted_change"] = False
    st["raw_voltage"] = raw
    st["candidate_age_ms"] = cand_age
    st["last_seen_ms"] = t
    return stable


def apply_guard(data: Dict[str, Any], mode: Dict[str, Any], config: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(data)
    ensure_shape(out)
    weights = mode.get("manual_field_weights") if isinstance(mode.get("manual_field_weights"), dict) else default_mode()["manual_field_weights"]
    timing = config.get("auto_timing") if isinstance(config.get("auto_timing"), dict) else {}
    auto_fields = bool(mode.get("auto_fields_enabled", False))
    auto_behavior = bool(mode.get("auto_behavior_enabled", False))
    auto_camera = bool(mode.get("auto_camera_enabled", False))

    if not auto_fields:
        set_channel(out, "/ch/2", "radial", sf(weights.get("radial"), 1.0), locked=True)
        set_channel(out, "/ch/3", "orbital", sf(weights.get("orbital"), 1.0), locked=True)
        set_channel(out, "/ch/4", "vertical", sf(weights.get("vertical"), 1.0), locked=True)
        set_channel(out, "/ch/5", "turbulence", sf(weights.get("turbulence"), 1.0), locked=True)
        set_channel(out, "/ch/6", "shell", sf(weights.get("shell"), 1.0), locked=True)
        scene = si(mode.get("manual_scene_index"), 0)
        set_channel(out, "/ch/8", "scene_index", float(clamp(scene, 0, 7)), locked=True)
        field_source = "manual_locked"
    else:
        raw_scene = get_channel_value(out, "/ch/8", "scene_index", 0.0)
        cand = voltage_to_step(raw_scene, 7)
        scene = slow_latch(state, "/ch/8", cand, si(timing.get("field_hold_ms"), 30000), si(timing.get("field_min_change_interval_ms"), 45000), si(mode.get("manual_scene_index"), 0))
        set_channel(out, "/ch/8", "scene_index", float(scene), raw=raw_scene, locked=False, source="slow_auto_fields")
        field_source = "slow_auto_fields"

    if not auto_behavior:
        behavior = si(mode.get("manual_behavior_code"), 0)
        set_channel(out, "/ch/18", "behavior_code", float(clamp(behavior, 0, 7)), locked=True)
        set_channel(out, "/ch/19", "behavior_authority_gate", 0.0, locked=True)
        behavior_source = "manual_locked"
    else:
        raw_behavior = get_channel_value(out, "/ch/18", "behavior_code", 0.0)
        cand_b = voltage_to_step(raw_behavior, 7)
        behavior = slow_latch(state, "/ch/18", cand_b, si(timing.get("behavior_hold_ms"), 30000), si(timing.get("behavior_min_change_interval_ms"), 45000), si(mode.get("manual_behavior_code"), 0))
        raw_gate = get_channel_value(out, "/ch/19", "behavior_authority_gate", 0.0)
        gate = slow_gate(state, "/ch/19", raw_gate, si(timing.get("gate_hold_ms"), 10000), sf(timing.get("gate_on_threshold"), 6.0), sf(timing.get("gate_off_threshold"), 4.0))
        set_channel(out, "/ch/18", "behavior_code", float(behavior), raw=raw_behavior, locked=False, source="slow_auto_behavior")
        set_channel(out, "/ch/19", "behavior_authority_gate", 10.0 if gate else 0.0, raw=raw_gate, locked=False, source="slow_auto_behavior_gate")
        behavior_source = "slow_auto_behavior"

    out["schema"] = out.get("schema") or "rmu.vcv_state.compatibility"
    out["version"] = out.get("version") or "unknown_source_bridge"
    out["hard_manual_authority"] = {
        "schema": "rmu.hard_manual_authority.runtime.v1",
        "version": VERSION,
        "updated_utc": utc(),
        "auto_fields_enabled": auto_fields,
        "auto_behavior_enabled": auto_behavior,
        "auto_camera_enabled": auto_camera,
        "field_source": field_source,
        "behavior_source": behavior_source,
        "camera": {
            "authority": "auto" if auto_camera else "keyboard_mouse",
            "manual_locked": not auto_camera,
            "scene_may_not_switch_camera": True,
            "behavior_may_not_switch_camera": True,
        },
        "locked_channels": sorted(CHANNELS.keys()),
    }
    out["stabilized_schema"] = "rmu.vcv_state_hard_manual_locked.v1"
    out["stabilized_version"] = VERSION
    out["stabilized_by"] = "src/runtime/hard_manual_authority_guard.py"
    out["stabilized_utc"] = utc()

    state["version"] = VERSION
    state["updated_utc"] = utc()
    state["write_count"] = si(state.get("write_count"), 0) + 1
    state["mode"] = {"auto_fields_enabled": auto_fields, "auto_behavior_enabled": auto_behavior, "auto_camera_enabled": auto_camera}
    state["effective"] = {
        "scene_index": si(out["mapped_values"].get("scene_index"), 0),
        "behavior_code": si(out["mapped_values"].get("behavior_code"), 0),
        "behavior_authority_gate": sf(out["mapped_values"].get("behavior_authority_gate"), 0.0),
        "field_weights": {name: sf(out["mapped_values"].get(name), 1.0) for name in ["radial", "orbital", "vertical", "turbulence", "shell"]},
    }
    return out


def run(root: Path, interval: float, once: bool, quiet: bool) -> int:
    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    log_path = output / "logs" / "hard_manual_authority_guard.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    vcv_path = output / "vcv_state.json"
    before_path = output / "vcv_state_before_hard_manual_guard.json"
    locked_path = output / "vcv_state_hard_manual_locked.json"
    state_path = output / "hard_manual_authority_guard_state.json"
    mode_path = output / "hard_manual_authority_mode.json"
    config_path = root / "config" / "hard_manual_authority.json"

    config, _ = read_json(config_path)
    if not config:
        config = {"auto_timing": {}}
    state = load_guard_state(state_path)

    if not quiet:
        print("============================================================")
        print("RealMathUniverse v1.7F Hard Manual Authority Guard")
        print(f"root: {root}")
        print(f"interval: {interval}")
        print("============================================================")

    while True:
        try:
            mode = load_mode(mode_path)
            data, err = read_json(vcv_path)
            if err:
                # Create a minimal vcv state so the renderer gets locked values even before first OSC packet.
                data = {"schema": "rmu.vcv_state.generated_by_guard", "version": VERSION, "status": "ACTIVE", "fresh": True}

            before = copy.deepcopy(data)
            before["preserved_before_hard_manual_guard_utc"] = utc()
            before["preserved_before_hard_manual_guard_by"] = VERSION
            atomic_write(before_path, before)

            locked = apply_guard(data, mode, config, state)
            atomic_write(locked_path, locked)
            atomic_write(state_path, state)
            atomic_write(vcv_path, locked)

            eff = state.get("effective", {})
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"{utc()} auto_fields={mode.get('auto_fields_enabled')} auto_behavior={mode.get('auto_behavior_enabled')} scene={eff.get('scene_index')} behavior={eff.get('behavior_code')} fields={eff.get('field_weights')}\n")
            if not quiet:
                print(f"[guard] scene={eff.get('scene_index')} behavior={eff.get('behavior_code')} fields={eff.get('field_weights')} auto_fields={mode.get('auto_fields_enabled')} auto_behavior={mode.get('auto_behavior_enabled')}")
            if once:
                return 0
            time.sleep(interval)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"{utc()} ERROR {type(exc).__name__}: {exc}\n")
            if not quiet:
                print(f"ERROR: {type(exc).__name__}: {exc}")
            if once:
                return 1
            time.sleep(max(interval, 0.05))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("RMU_ROOT", os.getcwd()))
    ap.add_argument("--interval", type=float, default=0.005)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    return run(Path(args.root).expanduser().resolve(), max(0.001, args.interval), args.once, args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
