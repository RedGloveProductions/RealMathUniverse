from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from control_queue_db import connect, insert_event
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parent))
    from control_queue_db import connect, insert_event

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import BlockingOSCUDPServer
except Exception:
    print("ERROR: python-osc is required. Install in venv: python3 -m pip install python-osc")
    raise


VERSION = "v1.10B_pure_vcv_truth_bridge"
SCHEMA = "rmu.vcv_state.v1_10B"


LABELS = {i: f"aux_{i}" for i in range(1, 33)}
LABELS.update(
    {
        1: "probability",
        2: "radial",
        3: "orbital",
        4: "vertical",
        5: "turbulence",
        6: "shell",
        7: "color_index",
        8: "behavior_vcv_gate",
        9: "particle_speed_bank_a",
        10: "species_mass_bank_a",
        11: "species_mass_bank_b",
        12: "particle_turbulence_bank_a",
        13: "particle_cohesion_bank_a",
        14: "gravity_well_position",
        15: "gravity_well_strength",
        16: "species_color_hsl_bank_a",
        17: "species_color_hsl_bank_b",
        18: "behavior_code",
        19: "color_trigger_gate",
        28: "probability_bank_b",
        29: "color_mode_bank_b",
        30: "particle_speed_bank_b",
        31: "particle_turbulence_bank_b",
        32: "particle_cohesion_bank_b",
    }
)

# Event queue recording only. This does not mean these channels become effective control.
STEPPED_EVENTS = {
    18: "behavior",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
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
        return data if isinstance(data, type(default)) else default
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class Bridge:
    def __init__(self, root: Path, host: str, port: int, heartbeat: float, timeout: float) -> None:
        self.root = root
        self.host = host
        self.port = port
        self.heartbeat = heartbeat
        self.timeout = timeout
        self.channels: Dict[str, Dict[str, Any]] = {}
        self.last_rx = 0.0
        self.rx_count = 0
        self.last_step: Dict[str, int] = {}
        self.conn = connect(root / "output/control_events.sqlite")
        self.writer_lock = root / "output/session_locks/vcv_state_writer.lock"
        self.writer_lock.parent.mkdir(parents=True, exist_ok=True)
        self.running = True

    def operator_mode(self) -> Dict[str, Any]:
        return read_json(self.root / "output/operator_authority_state.json", {})

    def voltage_to_step(self, value: float) -> int:
        return int(clamp(round(clamp(float(value), 0.0, 10.0) / 10.0 * 7.0), 0.0, 7.0))

    def handle(self, address: str, *args: Any) -> None:
        if not address.startswith("/ch/"):
            return

        try:
            channel_number = int(address.split("/")[-1])
        except Exception:
            return

        values: List[float] = []
        for arg in args:
            if isinstance(arg, (list, tuple)):
                values.extend(safe_float(x, 0.0) for x in arg)
            else:
                values.append(safe_float(arg, 0.0))

        if not values:
            values = [0.0]

        raw_value = values[0]
        now = time.time()
        label = LABELS.get(channel_number, f"aux_{channel_number}")

        self.rx_count += 1
        self.last_rx = now

        self.channels[address] = {
            "label": label,
            "raw": raw_value,
            "value": raw_value,
            "mapped": raw_value,
            "voices": values,
            "voice_count": len(values),
            "source": "vcv_raw",
            "updated_unix": now,
        }

        mode = self.operator_mode()
        if channel_number in STEPPED_EVENTS and bool(mode.get("vcv_event_recording_enabled", True)):
            step = self.voltage_to_step(raw_value)
            if self.last_step.get(address) != step:
                insert_event(
                    self.conn,
                    "vcv",
                    address,
                    STEPPED_EVENTS[channel_number],
                    raw_value,
                    step,
                    True,
                    250,
                )
                self.last_step[address] = step

        self.write_state()

    def write_state(self) -> None:
        mode = self.operator_mode()
        now = time.time()
        fresh = (now - self.last_rx) <= self.timeout if self.last_rx else False

        channels = dict(self.channels)

        mapped_values = {}
        labels = {}
        for channel, entry in channels.items():
            label = entry.get("label", channel)
            labels[channel] = label
            mapped_values[label] = entry.get("value", entry.get("raw", 0.0))

        writer = {
            "name": "vcv_osc_bridge",
            "version": VERSION,
            "pid": os.getpid(),
            "owns": ["output/vcv_state.json"],
            "lock": str(self.writer_lock),
        }

        output = {
            "schema": SCHEMA,
            "version": VERSION,
            "status": "ACTIVE" if fresh else "STALE",
            "fresh": fresh,
            "active": fresh,
            "rx_count": self.rx_count,
            "age_ms": int((now - self.last_rx) * 1000) if self.last_rx else None,
            "host": self.host,
            "port": self.port,
            "channels": channels,
            "direct_channels": channels,
            "raw_channels": channels,
            "mapped_values": mapped_values,
            "labels": labels,
            "operator_mode": {
                key: mode.get(key)
                for key in [
                    "auto_fields_enabled",
                    "auto_behavior_enabled",
                    "auto_camera_enabled",
                    "no_behavior_enabled",
                    "vcv_event_recording_enabled",
                    "vcv_continuous_enabled",
                    "dataset_coupling_mode",
                ]
            },
            "writer": writer,
            "updated_utc": utc_now_iso(),
        }

        atomic_write_json(self.root / "output/vcv_state.json", output)
        atomic_write_json(self.writer_lock, writer)

    def heartbeat_loop(self) -> None:
        while self.running:
            self.write_state()
            time.sleep(max(0.05, self.heartbeat))


def main() -> int:
    parser = argparse.ArgumentParser(description="RealMathUniverse pure VCV truth OSC bridge.")
    parser.add_argument("--project-root", "--root", dest="root", default=os.getcwd())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--heartbeat", type=float, default=0.25)
    parser.add_argument("--active-timeout", type=float, default=30.0)
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    bridge = Bridge(root, args.host, args.port, args.heartbeat, args.active_timeout)

    import threading
    threading.Thread(target=bridge.heartbeat_loop, daemon=True).start()

    dispatcher = Dispatcher()
    dispatcher.set_default_handler(bridge.handle)

    print(f"RealMathUniverse {VERSION} listening on {args.host}:{args.port}", flush=True)
    BlockingOSCUDPServer((args.host, args.port), dispatcher).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
