#!/usr/bin/env python3
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7E Nuclear Manual Authority VCV Bridge
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Replace the VCV bridge writer itself so dangerous channels are locked before
#   they ever become renderer-consumed VCV state.
#
# Locked by default:
#   /ch/2  radial
#   /ch/3  orbital
#   /ch/4  vertical
#   /ch/5  turbulence
#   /ch/6  shell
#   /ch/8  scene_index
#   /ch/18 behavior_code
#   /ch/19 behavior_authority_gate
#
# Unlocked channels still pass through:
#   probability, color, speed, mass/species banks, gravity, HSL, and reserved
#   channels.
#
# Why this is different from v1.7C/v1.7D:
#   This is not a downstream stabilizer. This is the source VCV JSON writer.
#   The renderer sees locked values directly in output/vcv_state.json and the
#   vcv block of output/control_state.json.
#
# Dependencies:
#   No required third-party Python packages. Uses a small OSC UDP parser for
#   float/int/bool messages from cvOSCcv. If python-osc exists, it is not needed.
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import socket
import struct
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

PATCH_VERSION = "1.7E-nuclear-manual-authority-bridge"
VCV_SCHEMA = "rmu.vcv_state.hard_manual_bridge.v1"
CONTROL_SCHEMA = "rmu.control_state.compat.v1"

CHANNEL_LABELS: Dict[int, str] = {
    1: "probability",
    2: "radial",
    3: "orbital",
    4: "vertical",
    5: "turbulence",
    6: "shell",
    7: "color_mode",
    8: "scene_index",
    9: "particle_speed",
    10: "species_mass_bank_a",
    11: "species_mass_bank_b",
    12: "particle_turbulence_bank_a",
    13: "particle_cohesion_bank_a",
    14: "gravity_well_position",
    15: "gravity_well_strength",
    16: "species_color_hsl_bank_a",
    17: "species_color_hsl_bank_b",
    18: "behavior_code",
    19: "behavior_authority_gate",
    20: "aux_20",
    21: "aux_21",
    22: "aux_22",
    23: "aux_23",
    24: "aux_24",
    25: "aux_25",
    26: "aux_26",
    27: "aux_27",
    28: "probability_bank_b",
    29: "color_mode_bank_b",
    30: "particle_speed_bank_b",
    31: "particle_turbulence_bank_b",
    32: "particle_cohesion_bank_b",
}

LOCKED_FIELD_CHANNELS = {2, 3, 4, 5, 6, 8}
LOCKED_BEHAVIOR_CHANNELS = {18, 19}
FIELD_LABEL_TO_CHANNEL = {
    "radial": 2,
    "orbital": 3,
    "vertical": 4,
    "turbulence": 5,
    "shell": 6,
}

RUNNING = True


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


def read_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_config(root: Path) -> Dict[str, Any]:
    default = {
        "osc": {"host": "127.0.0.1", "port": 9000, "send_port": 7001},
        "manual_defaults": {
            "scene_index": 0,
            "behavior_code": 0,
            "field_weights": {"radial": 1.0, "orbital": 1.0, "vertical": 1.0, "turbulence": 1.0, "shell": 1.0},
        },
        "auto_timing": {
            "scene_hold_ms": 30000,
            "scene_min_change_interval_ms": 45000,
            "behavior_hold_ms": 30000,
            "behavior_min_change_interval_ms": 45000,
            "gate_hold_ms": 10000,
            "gate_on_threshold": 6.0,
            "gate_off_threshold": 4.0,
        },
    }
    loaded = read_json(root / "config" / "hard_manual_authority.json")
    merged = dict(default)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            inner = dict(merged[key])
            inner.update(value)
            merged[key] = inner
        else:
            merged[key] = value
    return merged


def default_mode(config: Dict[str, Any]) -> Dict[str, Any]:
    defaults = config.get("manual_defaults", {}) if isinstance(config.get("manual_defaults"), dict) else {}
    weights = defaults.get("field_weights", {}) if isinstance(defaults.get("field_weights"), dict) else {}
    return {
        "schema": "rmu.manual_authority_mode.v1",
        "version": PATCH_VERSION,
        "auto_fields_enabled": False,
        "auto_behavior_enabled": False,
        "auto_camera_enabled": False,
        "manual_scene_index": safe_int(defaults.get("scene_index"), 0),
        "manual_behavior_code": safe_int(defaults.get("behavior_code"), 0),
        "manual_field_weights": {
            "radial": safe_float(weights.get("radial"), 1.0),
            "orbital": safe_float(weights.get("orbital"), 1.0),
            "vertical": safe_float(weights.get("vertical"), 1.0),
            "turbulence": safe_float(weights.get("turbulence"), 1.0),
            "shell": safe_float(weights.get("shell"), 1.0),
        },
    }


def load_mode(root: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    path = root / "output" / "manual_authority_mode.json"
    mode = default_mode(config)
    loaded = read_json(path)
    if loaded:
        mode.update(loaded)
        if not isinstance(mode.get("manual_field_weights"), dict):
            mode["manual_field_weights"] = default_mode(config)["manual_field_weights"]
    else:
        atomic_write_json(path, mode)
    return mode


def osc_pad_index(index: int) -> int:
    return (index + 4) & ~0x03


def parse_osc_string(packet: bytes, index: int) -> Tuple[str, int]:
    end = packet.find(b"\x00", index)
    if end < 0:
        raise ValueError("unterminated OSC string")
    text = packet[index:end].decode("utf-8", errors="replace")
    return text, osc_pad_index(end + 1)


def parse_osc_packet(packet: bytes) -> Optional[Tuple[str, List[Union[float, int, str, bool]]]]:
    """Minimal OSC parser for standard messages and simple bundles."""
    if not packet:
        return None

    # Bundle support: parse first message element after timetag, then ignore additional bundles.
    if packet.startswith(b"#bundle"):
        try:
            _, idx = parse_osc_string(packet, 0)
            idx += 8  # timetag
            if idx + 4 > len(packet):
                return None
            size = struct.unpack(">i", packet[idx:idx + 4])[0]
            idx += 4
            return parse_osc_packet(packet[idx:idx + size])
        except Exception:
            return None

    try:
        address, idx = parse_osc_string(packet, 0)
        if not address.startswith("/"):
            return None
        typetags, idx = parse_osc_string(packet, idx)
        if not typetags.startswith(","):
            return address, []
        args: List[Union[float, int, str, bool]] = []
        for tag in typetags[1:]:
            if tag == "f":
                if idx + 4 > len(packet):
                    break
                args.append(struct.unpack(">f", packet[idx:idx + 4])[0])
                idx += 4
            elif tag == "i":
                if idx + 4 > len(packet):
                    break
                args.append(struct.unpack(">i", packet[idx:idx + 4])[0])
                idx += 4
            elif tag == "h":
                if idx + 8 > len(packet):
                    break
                args.append(struct.unpack(">q", packet[idx:idx + 8])[0])
                idx += 8
            elif tag == "d":
                if idx + 8 > len(packet):
                    break
                args.append(struct.unpack(">d", packet[idx:idx + 8])[0])
                idx += 8
            elif tag == "s":
                text, idx = parse_osc_string(packet, idx)
                args.append(text)
            elif tag == "T":
                args.append(True)
            elif tag == "F":
                args.append(False)
            elif tag == "N":
                args.append(False)
            else:
                # Skip unknown fixed-width tags conservatively when possible.
                pass
        return address, args
    except Exception:
        return None


def channel_number_from_address(address: str) -> Optional[int]:
    if not address.startswith("/ch/"):
        return None
    suffix = address.split("/ch/", 1)[1].split("/", 1)[0]
    if not suffix.isdigit():
        return None
    n = int(suffix)
    if 1 <= n <= 32:
        return n
    return None


def scalar_or_list(args: List[Union[float, int, str, bool]]) -> Union[float, List[float]]:
    vals = [safe_float(a, 0.0) for a in args if not isinstance(a, str)]
    if not vals:
        return 0.0
    if len(vals) == 1:
        return vals[0]
    return vals


def first_value(value: Union[float, List[float]], default: float = 0.0) -> float:
    if isinstance(value, list):
        return safe_float(value[0], default) if value else default
    return safe_float(value, default)


def voltage_to_step(value: float, min_step: int = 0, max_step: int = 7) -> int:
    if 0.0 <= value <= float(max_step) and abs(value - round(value)) < 0.001:
        return int(clamp(round(value), min_step, max_step))
    return int(round(clamp(value / 10.0, 0.0, 1.0) * (max_step - min_step) + min_step))


def map_channel(n: int, value: Union[float, List[float]]) -> Union[float, int, List[float]]:
    def map_one(v: float) -> Union[float, int]:
        if n == 1:
            return clamp(v / 10.0, 0.0, 1.0)
        if n in {2, 3, 4, 5, 6}:
            # field weights, 0-10V to 0-3
            return clamp(v / 10.0 * 3.0, 0.0, 3.0)
        if n == 7:
            return voltage_to_step(v, 0, 4)
        if n == 8:
            return voltage_to_step(v, 0, 7)
        if n == 9:
            return clamp((v + 5.0) / 10.0 * 6.0 - 3.0, -3.0, 3.0)
        if n in {10, 11}:
            return clamp((v + 5.0) / 10.0 * 4.8 + 0.2, 0.2, 5.0)
        if n in {12, 31}:
            return clamp((v + 5.0) / 10.0 * 2.5, 0.0, 2.5)
        if n in {13, 32}:
            return clamp((v + 5.0) / 10.0 * 3.0, 0.0, 3.0)
        if n == 14:
            return clamp((v + 5.0) / 10.0 * 2.0 - 1.0, -1.0, 1.0)
        if n == 15:
            return clamp((v + 5.0) / 10.0 * 12.0, 0.0, 12.0)
        if n in {16, 17}:
            return clamp(v / 10.0, 0.0, 1.0)
        if n == 18:
            return voltage_to_step(v, 0, 7)
        if n == 19:
            return v
        if n in {28, 29, 30}:
            return v
        return v

    if isinstance(value, list):
        return [safe_float(map_one(safe_float(v))) for v in value]
    return map_one(safe_float(value))


def make_channel_entry(n: int, raw_value: Union[float, List[float]], mapped_value: Union[float, int, List[float]], locked: bool = False, source: str = "vcv") -> Dict[str, Any]:
    label = CHANNEL_LABELS.get(n, f"aux_{n}")
    entry: Dict[str, Any] = {
        "label": label,
        "raw": raw_value,
        "mapped": mapped_value,
        "value": mapped_value,
        "locked": locked,
        "source": source,
        "updated_utc": utc_now_iso(),
    }
    if isinstance(raw_value, list):
        entry["voices"] = raw_value
        entry["voice_count"] = len(raw_value)
    else:
        entry["voices"] = [raw_value]
        entry["voice_count"] = 1
    if isinstance(mapped_value, list):
        entry["mapped_voices"] = mapped_value
    else:
        entry["mapped_voices"] = [mapped_value]
    return entry


class SlowLatch:
    def __init__(self) -> None:
        self.scene_stable = 0
        self.scene_candidate = 0
        self.scene_candidate_since = now_ms()
        self.scene_last_change = 0
        self.behavior_stable = 0
        self.behavior_candidate = 0
        self.behavior_candidate_since = now_ms()
        self.behavior_last_change = 0
        self.gate_stable = 0
        self.gate_candidate = 0
        self.gate_candidate_since = now_ms()

    def step_latch(self, current: int, candidate: int, hold_ms: int, min_interval_ms: int, attr_prefix: str) -> int:
        t = now_ms()
        stable = getattr(self, f"{attr_prefix}_stable")
        old_candidate = getattr(self, f"{attr_prefix}_candidate")
        candidate_since = getattr(self, f"{attr_prefix}_candidate_since")
        last_change = getattr(self, f"{attr_prefix}_last_change")
        if candidate != old_candidate:
            setattr(self, f"{attr_prefix}_candidate", candidate)
            setattr(self, f"{attr_prefix}_candidate_since", t)
            return stable
        age = t - candidate_since
        change_age = t - last_change if last_change else 999999999
        if candidate != stable and age >= hold_ms and change_age >= min_interval_ms:
            setattr(self, f"{attr_prefix}_stable", candidate)
            setattr(self, f"{attr_prefix}_last_change", t)
            return candidate
        return stable

    def gate_latch(self, raw_voltage: float, hold_ms: int, on_threshold: float, off_threshold: float) -> int:
        t = now_ms()
        candidate = 0
        if self.gate_stable:
            candidate = 0 if raw_voltage <= off_threshold else 1
        else:
            candidate = 1 if raw_voltage >= on_threshold else 0
        if candidate != self.gate_candidate:
            self.gate_candidate = candidate
            self.gate_candidate_since = t
            return self.gate_stable
        if candidate != self.gate_stable and (t - self.gate_candidate_since) >= hold_ms:
            self.gate_stable = candidate
        return self.gate_stable

    def state(self) -> Dict[str, Any]:
        return {
            "scene_stable": self.scene_stable,
            "scene_candidate": self.scene_candidate,
            "behavior_stable": self.behavior_stable,
            "behavior_candidate": self.behavior_candidate,
            "gate_stable": self.gate_stable,
            "gate_candidate": self.gate_candidate,
        }


class Bridge:
    def __init__(self, root: Path, host: str, port: int, heartbeat: float, quiet: bool) -> None:
        self.root = root
        self.host = host
        self.port = port
        self.heartbeat = heartbeat
        self.quiet = quiet
        self.config = load_config(root)
        self.raw_channels: Dict[int, Union[float, List[float]]] = {}
        self.last_rx_ms = 0
        self.rx_count = 0
        self.latch = SlowLatch()
        self.lock = threading.RLock()
        self.vcv_path = root / "output" / "vcv_state.json"
        self.control_path = root / "output" / "control_state.json"
        self.log_path = root / "output" / "logs" / "vcv_osc_bridge_session.log"
        self.mode_path = root / "output" / "manual_authority_mode.json"

    def update_raw(self, n: int, raw_value: Union[float, List[float]]) -> None:
        with self.lock:
            self.raw_channels[n] = raw_value
            self.last_rx_ms = now_ms()
            self.rx_count += 1
            self.write_state()

    def build_state(self) -> Dict[str, Any]:
        self.config = load_config(self.root)
        mode = load_mode(self.root, self.config)
        auto_fields = bool(mode.get("auto_fields_enabled", False))
        auto_behavior = bool(mode.get("auto_behavior_enabled", False))
        auto_camera = bool(mode.get("auto_camera_enabled", False))
        manual_weights = mode.get("manual_field_weights", {}) if isinstance(mode.get("manual_field_weights"), dict) else {}
        timing = self.config.get("auto_timing", {}) if isinstance(self.config.get("auto_timing"), dict) else {}

        raw_snapshot = dict(self.raw_channels)
        channels: Dict[str, Dict[str, Any]] = {}
        direct_channels: Dict[str, Dict[str, Any]] = {}
        raw_channels_json: Dict[str, Any] = {}
        mapped_values: Dict[str, Any] = {}
        labels: Dict[str, str] = {}

        for n in range(1, 33):
            raw_value: Union[float, List[float]] = raw_snapshot.get(n, 0.0)
            mapped_value: Union[float, int, List[float]] = map_channel(n, raw_value)
            locked = False
            source = "vcv"

            # Manual field lock.
            if n in {2, 3, 4, 5, 6} and not auto_fields:
                label = CHANNEL_LABELS[n]
                raw_value = safe_float(manual_weights.get(label), 1.0)
                mapped_value = raw_value
                locked = True
                source = "manual_field_lock"

            if n == 8:
                if not auto_fields:
                    raw_value = safe_int(mode.get("manual_scene_index"), 0)
                    mapped_value = raw_value
                    locked = True
                    source = "manual_scene_lock"
                    self.latch.scene_stable = safe_int(mapped_value, 0)
                else:
                    raw_scene = first_value(raw_value, 0.0)
                    candidate = safe_int(map_channel(8, raw_scene), 0)
                    scene = self.latch.step_latch(
                        current=self.latch.scene_stable,
                        candidate=candidate,
                        hold_ms=safe_int(timing.get("scene_hold_ms"), 30000),
                        min_interval_ms=safe_int(timing.get("scene_min_change_interval_ms"), 45000),
                        attr_prefix="scene",
                    )
                    mapped_value = scene
                    source = "slow_auto_scene"

            # Manual behavior lock.
            if n == 18:
                if not auto_behavior:
                    raw_value = safe_int(mode.get("manual_behavior_code"), 0)
                    mapped_value = raw_value
                    locked = True
                    source = "manual_behavior_lock"
                    self.latch.behavior_stable = safe_int(mapped_value, 0)
                else:
                    raw_behavior = first_value(raw_value, 0.0)
                    candidate = safe_int(map_channel(18, raw_behavior), 0)
                    behavior = self.latch.step_latch(
                        current=self.latch.behavior_stable,
                        candidate=candidate,
                        hold_ms=safe_int(timing.get("behavior_hold_ms"), 30000),
                        min_interval_ms=safe_int(timing.get("behavior_min_change_interval_ms"), 45000),
                        attr_prefix="behavior",
                    )
                    mapped_value = behavior
                    source = "slow_auto_behavior"

            if n == 19:
                if not auto_behavior:
                    raw_value = 0.0
                    mapped_value = 0.0
                    locked = True
                    source = "manual_behavior_gate_lock"
                    self.latch.gate_stable = 0
                else:
                    raw_gate = first_value(raw_value, 0.0)
                    gate = self.latch.gate_latch(
                        raw_voltage=raw_gate,
                        hold_ms=safe_int(timing.get("gate_hold_ms"), 10000),
                        on_threshold=safe_float(timing.get("gate_on_threshold"), 6.0),
                        off_threshold=safe_float(timing.get("gate_off_threshold"), 4.0),
                    )
                    mapped_value = 10.0 if gate else 0.0
                    source = "slow_auto_behavior_gate"

            entry = make_channel_entry(n, raw_value, mapped_value, locked=locked, source=source)
            key = f"/ch/{n}"
            label = CHANNEL_LABELS.get(n, f"aux_{n}")
            channels[key] = entry
            direct_channels[key] = entry
            raw_channels_json[key] = raw_snapshot.get(n, 0.0)
            labels[key] = label
            mapped_values[label] = mapped_value

        active = (now_ms() - self.last_rx_ms) < 2500 if self.last_rx_ms else False
        payload = {
            "schema": VCV_SCHEMA,
            "version": PATCH_VERSION,
            "bridge_version": PATCH_VERSION,
            "updated_utc": utc_now_iso(),
            "active": active,
            "fresh": active,
            "status": "ACTIVE" if active else "WAITING_FOR_VCV",
            "host": self.host,
            "port": self.port,
            "rx_count": self.rx_count,
            "last_rx_age_ms": now_ms() - self.last_rx_ms if self.last_rx_ms else None,
            "manual_authority": {
                "enabled": True,
                "auto_fields_enabled": auto_fields,
                "auto_behavior_enabled": auto_behavior,
                "auto_camera_enabled": auto_camera,
                "locked_field_channels": ["/ch/2", "/ch/3", "/ch/4", "/ch/5", "/ch/6", "/ch/8"],
                "locked_behavior_channels": ["/ch/18", "/ch/19"],
                "camera_authority": "auto" if auto_camera else "keyboard_mouse",
                "camera_locked_manual": not auto_camera,
                "behavior_may_not_switch_camera": True,
                "scene_may_not_switch_camera": True,
                "latch": self.latch.state(),
            },
            "channels": channels,
            "direct_channels": direct_channels,
            "raw_channels": raw_channels_json,
            "mapped_values": mapped_values,
            "labels": labels,
        }

        # Compatibility top-level keys.
        for label, value in mapped_values.items():
            payload[label] = value
        for n in range(1, 33):
            payload[f"ch{n}"] = channels[f"/ch/{n}"]

        return payload

    def write_state(self) -> None:
        payload = self.build_state()
        atomic_write_json(self.vcv_path, payload)

        control = read_json(self.control_path)
        if not control:
            control = {"schema": CONTROL_SCHEMA, "version": PATCH_VERSION}
        control["updated_utc"] = utc_now_iso()
        control["vcv"] = {
            "schema": VCV_SCHEMA,
            "version": PATCH_VERSION,
            "active": payload.get("active"),
            "fresh": payload.get("fresh"),
            "status": payload.get("status"),
            "channels": payload.get("channels"),
            "mapped_values": payload.get("mapped_values"),
            "manual_authority": payload.get("manual_authority"),
        }
        control["manual_authority"] = payload.get("manual_authority")
        atomic_write_json(self.control_path, control)

    def serve(self) -> None:
        self.root.joinpath("output", "logs").mkdir(parents=True, exist_ok=True)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.settimeout(self.heartbeat)

        if not self.quiet:
            print("============================================================")
            print("RealMathUniverse v1.7E Nuclear Manual Authority VCV Bridge")
            print(f"Listening: {self.host}:{self.port}")
            print(f"Project:   {self.root}")
            print("Manual fields/behavior/camera are locked by default.")
            print("============================================================")

        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(f"{utc_now_iso()} START {PATCH_VERSION} {self.host}:{self.port}\n")

        self.write_state()
        last_heartbeat = time.monotonic()
        while RUNNING:
            try:
                packet, addr = sock.recvfrom(8192)
                parsed = parse_osc_packet(packet)
                if not parsed:
                    continue
                address, args = parsed
                n = channel_number_from_address(address)
                if n is None:
                    continue
                value = scalar_or_list(args)
                self.update_raw(n, value)
                if not self.quiet:
                    entry = self.build_state()["channels"][f"/ch/{n}"]
                    print(f"{address} raw={value} mapped={entry.get('mapped')} source={entry.get('source')} locked={entry.get('locked')}")
            except socket.timeout:
                if time.monotonic() - last_heartbeat >= self.heartbeat:
                    with self.lock:
                        self.write_state()
                    last_heartbeat = time.monotonic()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                with self.log_path.open("a", encoding="utf-8") as log:
                    log.write(f"{utc_now_iso()} ERROR {type(exc).__name__}: {exc}\n")
                if not self.quiet:
                    print(f"Bridge error: {type(exc).__name__}: {exc}", file=sys.stderr)
                time.sleep(0.1)

        sock.close()
        with self.log_path.open("a", encoding="utf-8") as log:
            log.write(f"{utc_now_iso()} STOP {PATCH_VERSION}\n")


def handle_signal(signum: int, frame: Any) -> None:
    global RUNNING
    RUNNING = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RealMathUniverse v1.7E hard manual authority VCV bridge.")
    parser.add_argument("--root", default=os.environ.get("RMU_ROOT", os.getcwd()), help="Project root")
    parser.add_argument("--host", default=None, help="OSC receive host")
    parser.add_argument("--port", type=int, default=None, help="OSC receive port")
    parser.add_argument("--heartbeat", type=float, default=0.25, help="State rewrite heartbeat seconds")
    parser.add_argument("--quiet", action="store_true", help="Reduce console output")
    return parser.parse_args()


def main() -> int:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    config = load_config(root)
    osc_cfg = config.get("osc", {}) if isinstance(config.get("osc"), dict) else {}
    host = args.host or str(osc_cfg.get("host", "127.0.0.1"))
    port = args.port or safe_int(osc_cfg.get("port"), 9000)
    bridge = Bridge(root=root, host=host, port=port, heartbeat=max(0.05, args.heartbeat), quiet=bool(args.quiet))
    bridge.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
