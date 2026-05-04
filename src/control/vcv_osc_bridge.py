"""
RealMathUniverse v0.9C3 VCV OSC Bridge

No profile system. No patch-specific assumptions.

Native cvOSCcv mapping:
    /ch/1  probability
    /ch/2  radial field weight
    /ch/3  orbital field weight
    /ch/4  vertical field weight
    /ch/5  turbulence field weight
    /ch/6  shell field weight
    /ch/7  color mode
    /ch/8  scene index
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: python-osc\n"
        "Install with:\n"
        "  cd /Users/Joe/Documents/RealMathUniverse\n"
        "  source .venv/bin/activate\n"
        "  python3 -m pip install python-osc\n"
    ) from exc


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(float(value), hi))


def normalize_cv(value: float) -> float:
    """Accept either 0-1 normalized control or 0-10V VCV-style CV."""
    value = float(value)
    if abs(value) > 1.5:
        return clamp(value / 10.0, 0.0, 1.0)
    return clamp(value, 0.0, 1.0)


def scale_cv(value: float, lo: float, hi: float) -> float:
    n = normalize_cv(value)
    return lo + (hi - lo) * n


class VCVOSCBridge:
    def __init__(self, project_root: Path, host: str, port: int, stale_after: float = 3.0):
        self.project_root = Path(project_root)
        self.host = host
        self.port = int(port)
        self.stale_after = float(stale_after)

        self.output_dir = self.project_root / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.vcv_state_path = self.output_dir / "vcv_state.json"
        self.control_state_path = self.output_dir / "control_state.json"

        self.values = {
            "probability_value": 0.0,
            "field_layer_weights": [0.25, 1.0, 0.1, 0.05, 0.2],
            "color_mode": 0,
            "scene_index": 0,
        }
        self.raw_channels = [0.0 for _ in range(8)]
        self.last_signal_time = 0.0

    def update_value(self, address: str, *args: Any) -> None:
        if not args:
            return

        try:
            value = float(args[0])
        except Exception:
            return

        if address in ("/ch/1", "/rmu/probability"):
            self.raw_channels[0] = value
            self.values["probability_value"] = normalize_cv(value)
        elif address in ("/ch/2", "/rmu/radial"):
            self.raw_channels[1] = value
            self.values["field_layer_weights"][0] = scale_cv(value, 0.0, 3.0)
        elif address in ("/ch/3", "/rmu/orbital"):
            self.raw_channels[2] = value
            self.values["field_layer_weights"][1] = scale_cv(value, 0.0, 3.0)
        elif address in ("/ch/4", "/rmu/vertical"):
            self.raw_channels[3] = value
            self.values["field_layer_weights"][2] = scale_cv(value, 0.0, 3.0)
        elif address in ("/ch/5", "/rmu/turbulence"):
            self.raw_channels[4] = value
            self.values["field_layer_weights"][3] = scale_cv(value, 0.0, 3.0)
        elif address in ("/ch/6", "/rmu/shell"):
            self.raw_channels[5] = value
            self.values["field_layer_weights"][4] = scale_cv(value, 0.0, 3.0)
        elif address in ("/ch/7", "/rmu/color"):
            self.raw_channels[6] = value
            self.values["color_mode"] = int(round(scale_cv(value, 0, 4)))
        elif address in ("/ch/8", "/rmu/scene"):
            self.raw_channels[7] = value
            self.values["scene_index"] = int(round(scale_cv(value, 1, 6)))
        else:
            return

        self.last_signal_time = time.time()
        self.write_state()
        print(f"VCV OSC {address} -> {value}")

    def write_state(self) -> None:
        now = time.time()
        external_detected = (now - self.last_signal_time) <= self.stale_after

        summary = (
            f"p={self.values['probability_value']:.2f} "
            f"r={self.values['field_layer_weights'][0]:.2f} "
            f"o={self.values['field_layer_weights'][1]:.2f} "
            f"v={self.values['field_layer_weights'][2]:.2f} "
            f"t={self.values['field_layer_weights'][3]:.2f} "
            f"s={self.values['field_layer_weights'][4]:.2f} "
            f"color={self.values['color_mode']} "
            f"scene={self.values['scene_index']}"
        )

        native_channels = {
            "/ch/1": "probability",
            "/ch/2": "radial",
            "/ch/3": "orbital",
            "/ch/4": "vertical",
            "/ch/5": "turbulence",
            "/ch/6": "shell",
            "/ch/7": "color",
            "/ch/8": "scene",
        }

        state = {
            "version": "0.9C3",
            "timestamp_unix": now,
            "updated_by": "vcv_osc_bridge_v0_9C3_no_profiles",
            "profile_system": "removed",
            "external_detected": external_detected,
            "probability_source": "vcv" if external_detected else "internal",
            "native_channels": native_channels,
            "raw_channels": self.raw_channels,
            "summary": summary,
            **self.values,
        }

        self.atomic_write_json(self.vcv_state_path, state)

        control = self.read_json(self.control_state_path, default={})
        control["vcv"] = {
            "version": "0.9C3",
            "profile_system": "removed",
            "external_detected": external_detected,
            "probability_source": state["probability_source"],
            "last_signal_unix": self.last_signal_time,
            "state_path": str(self.vcv_state_path),
            "native_channels": native_channels,
            "summary": summary,
        }
        control["timestamp_unix"] = now
        self.atomic_write_json(self.control_state_path, control)

    def read_json(self, path: Path, default: Any):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    def atomic_write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(path)

    def serve(self) -> None:
        dispatcher = Dispatcher()
        for addr in [
            "/ch/1", "/ch/2", "/ch/3", "/ch/4",
            "/ch/5", "/ch/6", "/ch/7", "/ch/8",
            "/rmu/probability", "/rmu/radial", "/rmu/orbital", "/rmu/vertical",
            "/rmu/turbulence", "/rmu/shell", "/rmu/color", "/rmu/scene",
        ]:
            dispatcher.map(addr, self.update_value)

        self.write_state()
        server = ThreadingOSCUDPServer((self.host, self.port), dispatcher)
        print(f"RealMathUniverse VCV OSC Bridge v0.9C3 listening on {self.host}:{self.port}")
        print("Profile system removed. No profile argument is accepted or needed.")
        print("Native VCV channels: /ch/1 probability, /ch/2 radial, /ch/3 orbital, /ch/4 vertical, /ch/5 turbulence, /ch/6 shell, /ch/7 color, /ch/8 scene")
        print(f"Writing state to {self.vcv_state_path}")
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default="/Users/Joe/Documents/RealMathUniverse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--stale-after", type=float, default=3.0)
    args = parser.parse_args()

    bridge = VCVOSCBridge(
        project_root=Path(args.project_root),
        host=args.host,
        port=args.port,
        stale_after=args.stale_after,
    )
    bridge.serve()


if __name__ == "__main__":
    main()
