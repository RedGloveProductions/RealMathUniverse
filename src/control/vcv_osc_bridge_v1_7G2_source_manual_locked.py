#!/usr/bin/env python3
"""
RealMathUniverse v1.7G2 Source Manual Locked VCV Bridge

This replaces the active VCV OSC bridge writer. It receives generic /ch/1 through
/ch/32 from cvOSCcv, but hard-locks field/scene/behavior authority channels at
the source unless slow auto mode is explicitly enabled in:

  output/manual_authority_mode.json

Locked by default:
  /ch/2 radial
  /ch/3 orbital
  /ch/4 vertical
  /ch/5 turbulence
  /ch/6 shell
  /ch/8 scene_index
  /ch/18 behavior_code
  /ch/19 behavior_authority_gate

VCV remains live for the other channels: probability, color, particle speed,
species banks, gravity, etc.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
except Exception as exc:
    print(f"FATAL: python-osc is required: {exc}", file=sys.stderr)
    raise

VERSION = "v1.7G2_source_manual_locked_bridge_fixed"
CHANNEL_COUNT = 32

LABELS = {
    "/ch/1": "probability",
    "/ch/2": "radial",
    "/ch/3": "orbital",
    "/ch/4": "vertical",
    "/ch/5": "turbulence",
    "/ch/6": "shell",
    "/ch/7": "color_mode",
    "/ch/8": "scene_index",
    "/ch/9": "particle_speed_bank_a",
    "/ch/10": "species_mass_bank_a",
    "/ch/11": "species_mass_bank_b",
    "/ch/12": "particle_turbulence_bank_a",
    "/ch/13": "particle_cohesion_bank_a",
    "/ch/14": "gravity_well_position",
    "/ch/15": "gravity_well_strength",
    "/ch/16": "species_color_hsl_bank_a",
    "/ch/17": "species_color_hsl_bank_b",
    "/ch/18": "behavior_code",
    "/ch/19": "behavior_authority_gate",
    "/ch/20": "aux_20",
    "/ch/21": "aux_21",
    "/ch/22": "aux_22",
    "/ch/23": "aux_23",
    "/ch/24": "aux_24",
    "/ch/25": "aux_25",
    "/ch/26": "aux_26",
    "/ch/27": "aux_27",
    "/ch/28": "probability_bank_b",
    "/ch/29": "color_mode_bank_b",
    "/ch/30": "particle_speed_bank_b",
    "/ch/31": "particle_turbulence_bank_b",
    "/ch/32": "particle_cohesion_bank_b",
}

FIELD_CHANNELS = {
    "/ch/2": "radial",
    "/ch/3": "orbital",
    "/ch/4": "vertical",
    "/ch/5": "turbulence",
    "/ch/6": "shell",
}

LOCKED_DEFAULTS = {
    "/ch/2": 1.0,
    "/ch/3": 1.0,
    "/ch/4": 1.0,
    "/ch/5": 1.0,
    "/ch/6": 1.0,
    "/ch/8": 0.0,
    "/ch/18": 0.0,
    "/ch/19": 0.0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_ms() -> int:
    return int(time.monotonic() * 1000)


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = -1
    tmp: Optional[Path] = None
    try:
        fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
        tmp = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp), str(path))
    finally:
        if fd != -1:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp is not None and tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if not path.exists():
            return dict(default)
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = dict(default)
            merged.update(data)
            return merged
        return dict(default)
    except Exception:
        return dict(default)


def default_mode() -> Dict[str, Any]:
    return {
        "schema": "rmu.manual_authority_mode.v1",
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


def voltage_to_step(v: float, max_step: int = 7) -> int:
    # Already step-like
    if 0 <= v <= max_step and abs(v - round(v)) < 0.001:
        return int(clamp(round(v), 0, max_step))
    return int(round(clamp(v, 0.0, 10.0) / 10.0 * max_step))


class ManualLockedBridge:
    def __init__(self, root: Path, host: str, port: int, write_hz: float):
        self.root = root
        self.host = host
        self.port = port
        self.write_interval = 1.0 / max(1.0, write_hz)
        self.output = root / "output" / "vcv_state.json"
        self.mode_path = root / "output" / "manual_authority_mode.json"
        self.log_path = root / "output" / "logs" / "vcv_osc_bridge_session.log"
        self.raw_channels: Dict[str, Any] = {}
        self.rx_count = 0
        self.last_rx_ms = 0
        self.start_ms = now_ms()
        self.running = True
        self.last_write = 0.0
        self.latch_state: Dict[str, Any] = {
            "/ch/8": {"stable": 0, "candidate": 0, "candidate_since_ms": now_ms(), "last_change_ms": 0},
            "/ch/18": {"stable": 0, "candidate": 0, "candidate_since_ms": now_ms(), "last_change_ms": 0},
            "/ch/19": {"stable": 0, "candidate": 0, "candidate_since_ms": now_ms(), "last_change_ms": 0},
        }
        self.root.joinpath("output/logs").mkdir(parents=True, exist_ok=True)
        if not self.mode_path.exists():
            atomic_write_json(self.mode_path, default_mode())

    def handle_signal(self, signum: int, frame: Any) -> None:
        self.running = False
        raise KeyboardInterrupt

    def on_channel(self, address: str, *args: Any) -> None:
        if address not in LABELS:
            return
        values: List[float] = [safe_float(a) for a in args]
        if not values:
            values = [0.0]
        self.raw_channels[address] = values if len(values) > 1 else values[0]
        self.rx_count += 1
        self.last_rx_ms = now_ms()
        if time.time() - self.last_write >= self.write_interval:
            self.write_state()

    def slow_latch(self, channel: str, candidate: int, hold_ms: int, min_interval_ms: int, fallback: int) -> int:
        t = now_ms()
        st = self.latch_state.setdefault(channel, {"stable": fallback, "candidate": fallback, "candidate_since_ms": t, "last_change_ms": 0})
        stable = int(st.get("stable", fallback))
        old_candidate = int(st.get("candidate", fallback))
        if candidate != old_candidate:
            st["candidate"] = candidate
            st["candidate_since_ms"] = t
            st["accepted_change"] = False
            return stable
        candidate_age = t - int(st.get("candidate_since_ms", t))
        change_age = t - int(st.get("last_change_ms", 0)) if int(st.get("last_change_ms", 0)) else 999999999
        if candidate != stable and candidate_age >= hold_ms and change_age >= min_interval_ms:
            stable = candidate
            st["stable"] = stable
            st["last_change_ms"] = t
            st["accepted_change"] = True
        else:
            st["accepted_change"] = False
        st["candidate_age_ms"] = candidate_age
        st["change_age_ms"] = change_age
        return stable

    def build_entry(self, ch: str, raw: Any, mapped: Any, locked: bool, source: str) -> Dict[str, Any]:
        label = LABELS.get(ch, ch)
        entry: Dict[str, Any] = {
            "label": label,
            "raw": raw,
            "mapped": mapped,
            "value": mapped,
            "locked": locked,
            "source": source,
            "bridge_version": VERSION,
        }
        if isinstance(raw, list):
            entry["voices"] = raw
            entry["voice_count"] = len(raw)
        return entry

    def write_state(self) -> None:
        mode = read_json(self.mode_path, default_mode())
        auto_fields = bool(mode.get("auto_fields_enabled", False))
        auto_behavior = bool(mode.get("auto_behavior_enabled", False))
        auto_camera = bool(mode.get("auto_camera_enabled", False))
        weights = mode.get("manual_field_weights") if isinstance(mode.get("manual_field_weights"), dict) else {}

        slow = read_json(self.root / "config" / "manual_authority_lock.json", {}).get("slow_auto", {})
        field_hold_ms = int(slow.get("field_hold_ms", 30000))
        field_min_ms = int(slow.get("field_min_change_interval_ms", 45000))
        behavior_hold_ms = int(slow.get("behavior_hold_ms", 30000))
        behavior_min_ms = int(slow.get("behavior_min_change_interval_ms", 45000))
        gate_hold_ms = int(slow.get("gate_hold_ms", 10000))
        gate_on = float(slow.get("gate_on_threshold", 6.0))
        gate_off = float(slow.get("gate_off_threshold", 4.0))

        channels: Dict[str, Dict[str, Any]] = {}
        direct: Dict[str, Dict[str, Any]] = {}
        labels: Dict[str, str] = {}
        mapped_values: Dict[str, Any] = {}
        raw_values: Dict[str, Any] = {}

        for i in range(1, CHANNEL_COUNT + 1):
            ch = f"/ch/{i}"
            raw = self.raw_channels.get(ch, 0.0)
            raw_values[ch] = raw
            label = LABELS.get(ch, f"aux_{i}")
            labels[ch] = label
            mapped: Any = raw
            locked = False
            source = "vcv_live"

            if ch in FIELD_CHANNELS:
                if not auto_fields:
                    mapped = float(weights.get(label, 1.0))
                    locked = True
                    source = "manual_locked_fields"
                else:
                    # Allow live field amplitudes in auto mode, but field recipe scene still slow latches.
                    mapped = raw
                    locked = False
                    source = "slow_auto_fields_live_weight"

            elif ch == "/ch/8":
                if not auto_fields:
                    mapped = float(int(mode.get("manual_scene_index", 0)))
                    locked = True
                    source = "manual_locked_scene"
                else:
                    raw_scalar = raw[0] if isinstance(raw, list) and raw else raw
                    cand = voltage_to_step(safe_float(raw_scalar), 7)
                    mapped = float(self.slow_latch(ch, cand, field_hold_ms, field_min_ms, int(mode.get("manual_scene_index", 0))))
                    source = "slow_auto_scene_latched"

            elif ch == "/ch/18":
                if not auto_behavior:
                    mapped = float(int(mode.get("manual_behavior_code", 0)))
                    locked = True
                    source = "manual_locked_behavior"
                else:
                    raw_scalar = raw[0] if isinstance(raw, list) and raw else raw
                    cand = voltage_to_step(safe_float(raw_scalar), 7)
                    mapped = float(self.slow_latch(ch, cand, behavior_hold_ms, behavior_min_ms, int(mode.get("manual_behavior_code", 0))))
                    source = "slow_auto_behavior_latched"

            elif ch == "/ch/19":
                if not auto_behavior:
                    mapped = 0.0
                    locked = True
                    source = "manual_locked_behavior_gate"
                else:
                    raw_scalar = safe_float(raw[0] if isinstance(raw, list) and raw else raw)
                    current = int(self.latch_state.get(ch, {}).get("stable", 0))
                    cand = 0 if (current and raw_scalar <= gate_off) else (1 if ((not current) and raw_scalar >= gate_on) else current)
                    mapped = 10.0 * float(self.slow_latch(ch, cand, gate_hold_ms, 0, 0))
                    source = "slow_auto_behavior_gate_latched"

            entry = self.build_entry(ch, raw, mapped, locked, source)
            channels[ch] = entry
            direct[ch] = entry
            mapped_values[label] = mapped

        state = {
            "schema": "rmu.vcv_state.v1.7G2",
            "version": VERSION,
            "status": "ACTIVE",
            "fresh": True,
            "active": True,
            "updated_utc": utc_now(),
            "host": self.host,
            "port": self.port,
            "rx_count": self.rx_count,
            "age_ms": max(0, now_ms() - self.last_rx_ms) if self.last_rx_ms else None,
            "channels": channels,
            "direct_channels": direct,
            "raw_channels": raw_values,
            "labels": labels,
            "mapped_values": mapped_values,
            "manual_authority_lock": {
                "version": VERSION,
                "auto_fields_enabled": auto_fields,
                "auto_behavior_enabled": auto_behavior,
                "auto_camera_enabled": auto_camera,
                "camera": {
                    "authority": "auto" if auto_camera else "keyboard_mouse",
                    "manual_locked": not auto_camera,
                    "scene_may_not_switch_camera": True,
                    "behavior_may_not_switch_camera": True,
                },
                "effective": {
                    "scene_index": mapped_values.get("scene_index"),
                    "behavior_code": mapped_values.get("behavior_code"),
                    "behavior_authority_gate": mapped_values.get("behavior_authority_gate"),
                    "field_weights": {
                        "radial": mapped_values.get("radial"),
                        "orbital": mapped_values.get("orbital"),
                        "vertical": mapped_values.get("vertical"),
                        "turbulence": mapped_values.get("turbulence"),
                        "shell": mapped_values.get("shell"),
                    },
                },
            },
            # compatibility top-level fields
            "radial": mapped_values.get("radial"),
            "orbital": mapped_values.get("orbital"),
            "vertical": mapped_values.get("vertical"),
            "turbulence": mapped_values.get("turbulence"),
            "shell": mapped_values.get("shell"),
            "scene_index": mapped_values.get("scene_index"),
            "behavior_code": mapped_values.get("behavior_code"),
            "behavior_authority_gate": mapped_values.get("behavior_authority_gate"),
        }
        atomic_write_json(self.output, state)
        atomic_write_json(self.root / "output" / "manual_authority_bridge_state.json", state["manual_authority_lock"])
        self.last_write = time.time()

    def run(self) -> int:
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        dispatcher = Dispatcher()
        for i in range(1, CHANNEL_COUNT + 1):
            dispatcher.map(f"/ch/{i}", self.on_channel)
        # also catch anything under /ch just in case
        server = BlockingOSCUDPServer((self.host, self.port), dispatcher)
        print(f"RMU {VERSION} listening on {self.host}:{self.port}")
        print("Manual locked by default: /ch/2-/ch/6, /ch/8, /ch/18, /ch/19")
        self.write_state()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                server.server_close()
            except Exception:
                pass
            self.write_state()
        return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=os.environ.get("RMU_ROOT", os.getcwd()))
    p.add_argument("--host", default=os.environ.get("RMU_OSC_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("RMU_OSC_PORT", "9000")))
    p.add_argument("--write-hz", type=float, default=float(os.environ.get("RMU_VCV_WRITE_HZ", "30")))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    root.joinpath("output").mkdir(exist_ok=True)
    bridge = ManualLockedBridge(root=root, host=args.host, port=args.port, write_hz=args.write_hz)
    return bridge.run()


if __name__ == "__main__":
    raise SystemExit(main())
