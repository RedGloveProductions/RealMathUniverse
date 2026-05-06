#!/usr/bin/env python3
"""
RealMathUniverse v1.3F8 VCV OSC Bridge

Clean channel map based on the v1.3F5 /ch/10 pattern.
"""
from __future__ import annotations
import argparse, json, os, tempfile, time
from pathlib import Path
from typing import Any
try:
    from pythonosc.dispatcher import Dispatcher
    from pythonosc.osc_server import ThreadingOSCUDPServer
except ImportError as exc:
    raise SystemExit("Missing dependency: python-osc\nInstall with:\n  cd /Users/Joe/Documents/RealMathUniverse\n  source .venv/bin/activate\n  python3 -m pip install python-osc\n") from exc

CHANNEL_LABELS = {1:"probability",2:"radial",3:"orbital",4:"vertical",5:"turbulence",6:"shell",7:"color",8:"scene",9:"particle_speed",10:"particle_mass",11:"particle_turbulence",12:"particle_cohesion"}
for _i in range(13, 33):
    CHANNEL_LABELS[_i] = f"aux_{_i}"

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(float(value), hi))

def normalize_0_1_or_0_10(value: float) -> float:
    value = float(value)
    if abs(value) > 1.5:
        return clamp(value / 10.0, 0.0, 1.0)
    return clamp(value, 0.0, 1.0)

def scale_cv(value: float, lo: float, hi: float) -> float:
    n = normalize_0_1_or_0_10(value)
    return lo + (hi - lo) * n

def clamp_bipolar_5v(value: float) -> float:
    return clamp(float(value), -5.0, 5.0)

def particle_speed_from_bipolar(value: float) -> float:
    return clamp((clamp_bipolar_5v(value) / 5.0) * 3.0, -3.0, 3.0)

def particle_mass_from_bipolar(value: float) -> float:
    n = (clamp_bipolar_5v(value) + 5.0) / 10.0
    return 0.20 + n * 4.80

def particle_turbulence_from_bipolar(value: float) -> float:
    n = (clamp_bipolar_5v(value) + 5.0) / 10.0
    return clamp(n * 2.50, 0.0, 2.50)

def particle_cohesion_from_bipolar(value: float) -> float:
    n = (clamp_bipolar_5v(value) + 5.0) / 10.0
    return clamp(n * 3.00, 0.0, 3.00)

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
            "scene_index": 1,
            "particle_speed_raw": 0.0,
            "particle_speed": 1.0,
            "particle_mass_raw": 0.0,
            "particle_mass": 1.0,
            "particle_turbulence_raw": 0.0,
            "particle_turbulence": 0.0,
            "particle_cohesion_raw": 0.0,
            "particle_cohesion": 0.0,
            "aux_channels": {f"/ch/{i}": 0.0 for i in range(13, 33)},
        }
        self.raw_channels = [0.0 for _ in range(32)]
        self.normalized_channels = [0.0 for _ in range(32)]
        self.channel_counts = [0 for _ in range(32)]
        self.channel_last_seen = [0.0 for _ in range(32)]
        self.last_signal_time = 0.0

    def update_value(self, address: str, *args: Any) -> None:
        if not args:
            return
        try:
            value = float(args[0])
        except Exception:
            return
        try:
            if not address.startswith("/ch/"):
                legacy = {"/rmu/probability":1,"/rmu/radial":2,"/rmu/orbital":3,"/rmu/vertical":4,"/rmu/turbulence":5,"/rmu/shell":6,"/rmu/color":7,"/rmu/scene":8,"/rmu/speed":9,"/rmu/particle_speed":9,"/rmu/mass":10,"/rmu/particle_mass":10,"/rmu/particle_turbulence":11,"/rmu/turbulence_particle":11,"/rmu/particle_cohesion":12,"/rmu/cohesion":12}
                ch = legacy.get(address)
                if ch is None:
                    return
            else:
                ch = int(address.split("/")[-1])
        except Exception:
            return
        if ch < 1 or ch > 32:
            return
        idx = ch - 1
        now = time.time()
        self.raw_channels[idx] = value
        self.normalized_channels[idx] = normalize_0_1_or_0_10(value)
        self.channel_counts[idx] += 1
        self.channel_last_seen[idx] = now
        if ch == 1:
            self.values["probability_value"] = normalize_0_1_or_0_10(value)
        elif ch == 2:
            self.values["field_layer_weights"][0] = scale_cv(value, 0.0, 3.0)
        elif ch == 3:
            self.values["field_layer_weights"][1] = scale_cv(value, 0.0, 3.0)
        elif ch == 4:
            self.values["field_layer_weights"][2] = scale_cv(value, 0.0, 3.0)
        elif ch == 5:
            self.values["field_layer_weights"][3] = scale_cv(value, 0.0, 3.0)
        elif ch == 6:
            self.values["field_layer_weights"][4] = scale_cv(value, 0.0, 3.0)
        elif ch == 7:
            self.values["color_mode"] = int(round(scale_cv(value, 0, 4)))
        elif ch == 8:
            self.values["scene_index"] = int(round(scale_cv(value, 1, 6)))
        elif ch == 9:
            self.values["particle_speed_raw"] = value
            self.values["particle_speed"] = particle_speed_from_bipolar(value)
        elif ch == 10:
            self.values["particle_mass_raw"] = value
            self.values["particle_mass"] = particle_mass_from_bipolar(value)
        elif ch == 11:
            self.values["particle_turbulence_raw"] = value
            self.values["particle_turbulence"] = particle_turbulence_from_bipolar(value)
        elif ch == 12:
            self.values["particle_cohesion_raw"] = value
            self.values["particle_cohesion"] = particle_cohesion_from_bipolar(value)
        else:
            self.values["aux_channels"][f"/ch/{ch}"] = value
        self.last_signal_time = now
        self.write_state()
        print(f"VCV OSC {address} -> {value}")

    def write_state(self) -> None:
        now = time.time()
        external_detected = (now - self.last_signal_time) <= self.stale_after
        native_channels = {f"/ch/{i}": CHANNEL_LABELS[i] for i in range(1, 33)}
        channel_active = {f"/ch/{i}": self.channel_last_seen[i - 1] > 0.0 and (now - self.channel_last_seen[i - 1]) <= self.stale_after for i in range(1, 33)}
        summary = (
            f"p={self.values['probability_value']:.2f} r={self.values['field_layer_weights'][0]:.2f} "
            f"o={self.values['field_layer_weights'][1]:.2f} v={self.values['field_layer_weights'][2]:.2f} "
            f"t={self.values['field_layer_weights'][3]:.2f} s={self.values['field_layer_weights'][4]:.2f} "
            f"color={self.values['color_mode']} scene={self.values['scene_index']} "
            f"speed={self.values['particle_speed']:.2f} raw9={self.values['particle_speed_raw']:.2f} "
            f"mass={self.values['particle_mass']:.2f} raw10={self.values['particle_mass_raw']:.2f} "
            f"turb={self.values['particle_turbulence']:.2f} raw11={self.values['particle_turbulence_raw']:.2f} "
            f"coh={self.values['particle_cohesion']:.2f} raw12={self.values['particle_cohesion_raw']:.2f}"
        )
        state = {"version":"1.3F8","timestamp_unix":now,"updated_by":"vcv_osc_bridge_v1_3F8_ch1_to_ch32_speed_mass_turbulence_cohesion","profile_system":"removed","external_detected":external_detected,"probability_source":"vcv" if external_detected else "internal","native_channels":native_channels,"channel_active":channel_active,"channel_counts":{f"/ch/{i}": self.channel_counts[i - 1] for i in range(1,33)},"channel_last_seen_unix":{f"/ch/{i}": self.channel_last_seen[i - 1] for i in range(1,33)},"raw_channels":self.raw_channels,"raw_channel_values":self.raw_channels,"normalized_channels":self.normalized_channels,"summary":summary, **self.values}
        self.atomic_write_json(self.vcv_state_path, state)
        control = self.read_json(self.control_state_path, default={})
        control["vcv"] = {"version":"1.3F8","profile_system":"removed","external_detected":external_detected,"probability_source":state["probability_source"],"last_signal_unix":self.last_signal_time,"state_path":str(self.vcv_state_path),"native_channels":native_channels,"channel_active":channel_active,"raw_channels":self.raw_channels,"normalized_channels":self.normalized_channels,"particle_speed":self.values["particle_speed"],"particle_speed_raw":self.values["particle_speed_raw"],"particle_mass":self.values["particle_mass"],"particle_mass_raw":self.values["particle_mass_raw"],"particle_turbulence":self.values["particle_turbulence"],"particle_turbulence_raw":self.values["particle_turbulence_raw"],"particle_cohesion":self.values["particle_cohesion"],"particle_cohesion_raw":self.values["particle_cohesion_raw"],"summary":summary}
        control["particle_speed"] = self.values["particle_speed"]
        control["particle_mass"] = self.values["particle_mass"]
        control["particle_turbulence"] = self.values["particle_turbulence"]
        control["particle_cohesion"] = self.values["particle_cohesion"]
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
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.write("\n")
            os.replace(tmp_name, path)
        finally:
            try:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            except Exception:
                pass

    def serve(self) -> None:
        dispatcher = Dispatcher()
        for i in range(1, 33):
            dispatcher.map(f"/ch/{i}", self.update_value)
        for addr in ["/rmu/probability","/rmu/radial","/rmu/orbital","/rmu/vertical","/rmu/turbulence","/rmu/shell","/rmu/color","/rmu/scene","/rmu/speed","/rmu/particle_speed","/rmu/mass","/rmu/particle_mass","/rmu/particle_turbulence","/rmu/turbulence_particle","/rmu/particle_cohesion","/rmu/cohesion"]:
            dispatcher.map(addr, self.update_value)
        self.write_state()
        server = ThreadingOSCUDPServer((self.host, self.port), dispatcher)
        print(f"RealMathUniverse VCV OSC Bridge v1.3F8 listening on {self.host}:{self.port}")
        print("Native VCV channels: /ch/1-/ch/32")
        print("/ch/9  particle_speed      bipolar -5V..+5V -> -3.00..+3.00")
        print("/ch/10 particle_mass       bipolar -5V..+5V ->  0.20..5.00")
        print("/ch/11 particle_turbulence bipolar -5V..+5V ->  0.00..2.50")
        print("/ch/12 particle_cohesion   bipolar -5V..+5V ->  0.00..3.00")
        print(f"Writing state to {self.vcv_state_path}")
        server.serve_forever()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default="/Users/Joe/Documents/RealMathUniverse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--stale-after", type=float, default=3.0)
    args = parser.parse_args()
    bridge = VCVOSCBridge(project_root=Path(args.project_root), host=args.host, port=args.port, stale_after=args.stale_after)
    bridge.serve()

if __name__ == "__main__":
    main()
