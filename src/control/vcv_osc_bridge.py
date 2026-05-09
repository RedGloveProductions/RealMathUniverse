#!/usr/bin/env python3
from __future__ import annotations

import argparse
import colorsys
import json
import math
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from pythonosc import dispatcher
from pythonosc import osc_server


VERSION = "v1.6D1_direct_32_channel_bridge"

SPECIES_NAMES = [
    "crab_default",
    "electron",
    "positron",
    "electron_neutrino",
    "up_quark",
    "down_quark",
    "photon_like",
    "gluon_like",
    "higgs_excitation",
    "proton_like",
    "neutron_like",
    "muon",
    "tau",
    "muon_neutrino",
    "tau_neutrino",
    "strange_quark",
    "charm_quark",
    "top_quark",
    "bottom_quark",
    "W_like",
    "Z_like",
    "meson_like",
]

NATIVE_CHANNELS = {
    "/ch/1": "probability",
    "/ch/2": "radial",
    "/ch/3": "orbital",
    "/ch/4": "vertical",
    "/ch/5": "turbulence",
    "/ch/6": "shell",
    "/ch/7": "color_mode",
    "/ch/8": "scene_index",
    "/ch/9": "particle_speed",
    "/ch/10": "species_mass_bank_A",
    "/ch/11": "species_mass_bank_B",
    "/ch/12": "particle_turbulence_bank_A",
    "/ch/13": "particle_cohesion_bank_A",
    "/ch/14": "gravity_well_position",
    "/ch/15": "gravity_well_strength",
    "/ch/16": "species_color_hsl_bank_A",
    "/ch/17": "species_color_hsl_bank_B",
    "/ch/18": "behavior_code",
    "/ch/19": "behavior_authority_gate",
    "/ch/20": "adaptive_aux_20",
    "/ch/21": "adaptive_aux_21",
    "/ch/22": "adaptive_aux_22",
    "/ch/23": "adaptive_aux_23",
    "/ch/24": "adaptive_aux_24",
    "/ch/25": "adaptive_aux_25",
    "/ch/26": "adaptive_aux_26",
    "/ch/27": "adaptive_aux_27",
    "/ch/28": "probability_bank_B",
    "/ch/29": "color_mode_bank_B",
    "/ch/30": "particle_speed_bank_B",
    "/ch/31": "particle_turbulence_bank_B",
    "/ch/32": "particle_cohesion_bank_B",
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def flatten_args(args: tuple[Any, ...]) -> list[float]:
    out: list[float] = []

    def walk(x: Any) -> None:
        if isinstance(x, (list, tuple)):
            for item in x:
                walk(item)
            return
        try:
            value = float(x)
        except Exception:
            return
        if math.isfinite(value):
            out.append(value)

    for arg in args:
        walk(arg)

    return out


def first(values: list[float], default: float = 0.0) -> float:
    return values[0] if values else default


def pad_bank(values: list[float], count: int, fill: float = 0.0) -> list[float]:
    out = list(values[:count])
    while len(out) < count:
        out.append(fill)
    return out


def split_22(bank_a: list[float], bank_b: list[float], fallback: float = 0.0) -> list[float]:
    merged = list(bank_a[:16]) + list(bank_b[:6])
    return pad_bank(merged, 22, fallback)


def map_0_10_to_0_1(v: float) -> float:
    return clamp(v / 10.0, 0.0, 1.0)


def map_field_0_10_to_0_3(v: float) -> float:
    return clamp((v / 10.0) * 3.0, 0.0, 3.0)


def map_mass_neg5_pos5_to_0p2_5(v: float) -> float:
    return clamp(0.2 + ((clamp(v, -5.0, 5.0) + 5.0) / 10.0) * 4.8, 0.2, 5.0)


def map_neg5_pos5_to_0_3(v: float) -> float:
    return clamp(((clamp(v, -5.0, 5.0) + 5.0) / 10.0) * 3.0, 0.0, 3.0)


def map_speed_neg5_pos5_to_neg3_pos3(v: float) -> float:
    return clamp((clamp(v, -5.0, 5.0) / 5.0) * 3.0, -3.0, 3.0)


def map_color_mode(v: float) -> int:
    return int(clamp(round(v / 2.5), 0, 4))


def map_scene(v: float) -> int:
    return int(clamp(round(v / 2.0) + 1, 1, 6))


def map_behavior_code(v: float) -> int:
    return int(clamp(round(v), 0, 7))


def hsl_voltage_to_rgb_hex(v: float, species_index: int) -> tuple[list[float], str]:
    # 0..10V sweeps hue, with a tiny species phase offset so repeated values still separate visually.
    hue = ((clamp(v, 0.0, 10.0) / 10.0) + (species_index * 0.037)) % 1.0
    sat = 0.68
    light = 0.58
    r, g, b = colorsys.hls_to_rgb(hue, light, sat)
    rgb = [float(r), float(g), float(b)]
    hx = "#{:02X}{:02X}{:02X}".format(
        int(clamp(r, 0.0, 1.0) * 255.0),
        int(clamp(g, 0.0, 1.0) * 255.0),
        int(clamp(b, 0.0, 1.0) * 255.0),
    )
    return rgb, hx


class VCVOSCBridge:
    def __init__(
        self,
        project_root: Path,
        host: str,
        port: int,
        heartbeat: float,
        active_timeout: float,
    ) -> None:
        self.project_root = project_root
        self.host = host
        self.port = port
        self.heartbeat = heartbeat
        self.active_timeout = active_timeout

        self.output_dir = self.project_root / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.output_dir / "vcv_state.json"

        self.lock = threading.RLock()
        self.running = True
        self.raw_channels: dict[str, list[float]] = {f"/ch/{i}": [] for i in range(1, 33)}
        self.message_count = 0
        self.write_count = 0
        self.last_message_time = 0.0
        self.started_time = time.time()

    def handle_channel(self, address: str, *args: Any) -> None:
        values = flatten_args(args)

        if not address.startswith("/ch/"):
            return

        try:
            number = int(address.split("/")[-1])
        except Exception:
            return

        if number < 1 or number > 32:
            return

        with self.lock:
            self.raw_channels[address] = values
            self.message_count += 1
            self.last_message_time = time.time()

    def generic_handler(self, address: str, *args: Any) -> None:
        self.handle_channel(address, *args)

    def mapped_scalar_for_channel(self, channel: str, values: list[float]) -> float:
        v = first(values, 0.0)

        if channel == "/ch/1":
            return map_0_10_to_0_1(v)
        if channel in {"/ch/2", "/ch/3", "/ch/4", "/ch/5", "/ch/6"}:
            return map_field_0_10_to_0_3(v)
        if channel == "/ch/7":
            return float(map_color_mode(v))
        if channel == "/ch/8":
            return float(map_scene(v))
        if channel == "/ch/9":
            return map_speed_neg5_pos5_to_neg3_pos3(v)
        if channel in {"/ch/10", "/ch/11"}:
            return map_mass_neg5_pos5_to_0p2_5(v)
        if channel in {"/ch/12", "/ch/13"}:
            return map_neg5_pos5_to_0_3(v)
        if channel == "/ch/14":
            return v
        if channel == "/ch/15":
            return clamp(v, 0.0, 10.0)
        if channel in {"/ch/16", "/ch/17"}:
            return clamp(v, 0.0, 10.0)
        if channel == "/ch/18":
            return float(map_behavior_code(v))
        if channel == "/ch/19":
            return v
        if channel in {"/ch/28"}:
            return map_0_10_to_0_1(v)
        if channel in {"/ch/29"}:
            return float(map_color_mode(v))
        if channel in {"/ch/30"}:
            return map_speed_neg5_pos5_to_neg3_pos3(v)
        if channel in {"/ch/31", "/ch/32"}:
            return map_neg5_pos5_to_0_3(v)

        return v

    def build_species_banks(self) -> dict[str, Any]:
        raw = self.raw_channels

        probability_raw = split_22(raw.get("/ch/1", []), raw.get("/ch/28", []), first(raw.get("/ch/1", []), 0.0))
        probability = [map_0_10_to_0_1(v) for v in probability_raw]

        color_mode_raw = split_22(raw.get("/ch/7", []), raw.get("/ch/29", []), first(raw.get("/ch/7", []), 0.0))
        color_mode = [map_color_mode(v) for v in color_mode_raw]

        speed_raw = split_22(raw.get("/ch/9", []), raw.get("/ch/30", []), first(raw.get("/ch/9", []), 0.0))
        speed = [map_speed_neg5_pos5_to_neg3_pos3(v) for v in speed_raw]

        mass_raw = split_22(raw.get("/ch/10", []), raw.get("/ch/11", []), first(raw.get("/ch/10", []), 0.0))
        mass = [map_mass_neg5_pos5_to_0p2_5(v) for v in mass_raw]

        turbulence_raw = split_22(raw.get("/ch/12", []), raw.get("/ch/31", []), first(raw.get("/ch/12", []), 0.0))
        turbulence = [map_neg5_pos5_to_0_3(v) for v in turbulence_raw]

        cohesion_raw = split_22(raw.get("/ch/13", []), raw.get("/ch/32", []), first(raw.get("/ch/13", []), 0.0))
        cohesion = [map_neg5_pos5_to_0_3(v) for v in cohesion_raw]

        color_hsl_raw = split_22(raw.get("/ch/16", []), raw.get("/ch/17", []), first(raw.get("/ch/16", []), 5.0))
        color_rgb: list[float] = []
        color_hex: list[str] = []
        for i, v in enumerate(color_hsl_raw):
            rgb, hx = hsl_voltage_to_rgb_hex(v, i)
            color_rgb.extend(rgb)
            color_hex.append(hx)

        grav_raw = pad_bank(raw.get("/ch/14", []), 4, 0.0)
        gravity_vec4 = [float(grav_raw[0]), float(grav_raw[1]), float(grav_raw[2]), float(grav_raw[3])]
        gravity_strength = clamp(first(raw.get("/ch/15", []), 0.0), 0.0, 10.0)

        return {
            "particle_species_probability_raw": probability_raw,
            "particle_species_probability": probability,
            "particle_species_color_mode_raw": color_mode_raw,
            "particle_species_color_mode": color_mode,
            "particle_species_speed_raw": speed_raw,
            "particle_species_speed": speed,
            "particle_species_mass_raw": mass_raw,
            "particle_species_mass": mass,
            "particle_species_turbulence_raw": turbulence_raw,
            "particle_species_turbulence": turbulence,
            "particle_species_cohesion_raw": cohesion_raw,
            "particle_species_cohesion": cohesion,
            "particle_species_color_hsl_raw": color_hsl_raw,
            "particle_species_color_rgb": color_rgb,
            "particle_species_color_hex": color_hex,
            "gravity_well_position_vec4": gravity_vec4,
            "gravity_well_position_raw": grav_raw,
            "gravity_well_strength": gravity_strength,
        }

    def build_state(self) -> dict[str, Any]:
        now = time.time()
        active = self.last_message_time > 0 and (now - self.last_message_time) <= self.active_timeout
        fresh = active
        stale = not active

        raw_channels_out: dict[str, list[float]] = {}
        channels_out: dict[str, float] = {}
        voice_counts: dict[str, int] = {}

        for i in range(1, 33):
            channel = f"/ch/{i}"
            values = list(self.raw_channels.get(channel, []))
            raw_channels_out[channel] = values
            channels_out[channel] = self.mapped_scalar_for_channel(channel, values)
            voice_counts[channel] = len(values)

        scene = int(channels_out["/ch/8"])
        color = int(channels_out["/ch/7"])
        behavior_code = int(channels_out["/ch/18"])
        behavior_gate = float(channels_out["/ch/19"])
        behavior_gate_active = voice_counts["/ch/19"] > 0 and behavior_gate >= 5.0

        banks = self.build_species_banks()

        state: dict[str, Any] = {
            "version": VERSION,
            "status": "ACTIVE" if active else "VCV_STALE",
            "active": active,
            "fresh": fresh,
            "stale": stale,
            "timestamp_unix": now,
            "started_time_unix": self.started_time,
            "last_message_time_unix": self.last_message_time,
            "message_count": self.message_count,
            "write_count": self.write_count,
            "host": self.host,
            "port": self.port,
            "native_channels": NATIVE_CHANNELS,
            "raw_channels": raw_channels_out,
            "channels": channels_out,
            "channel_voice_counts": voice_counts,

            # Compatibility aliases for older monitors / renderer code.
            "native_channel_values": channels_out,
            "native_raw_channels": raw_channels_out,
            "native_channel_voice_counts": voice_counts,

            "scene_index": scene,
            "color_mode": color,
            "behavior_code": behavior_code,
            "behavior_authority_gate": behavior_gate,
            "behavior_authority_active": behavior_gate_active,

            "probability": channels_out["/ch/1"],
            "radial": channels_out["/ch/2"],
            "orbital": channels_out["/ch/3"],
            "vertical": channels_out["/ch/4"],
            "turbulence": channels_out["/ch/5"],
            "shell": channels_out["/ch/6"],
            "particle_speed": channels_out["/ch/9"],
            "particle_mass": channels_out["/ch/10"],
            "particle_turbulence": channels_out["/ch/12"],
            "particle_cohesion": channels_out["/ch/13"],
        }

        state.update(banks)
        return state

    def atomic_write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
            tmp_name = f.name

        os.replace(tmp_name, path)

    def writer_loop(self) -> None:
        while self.running:
            with self.lock:
                state = self.build_state()
                self.write_count += 1
                state["write_count"] = self.write_count
                self.atomic_write_json(self.state_path, state)
            time.sleep(self.heartbeat)

    def serve(self) -> None:
        print("=" * 72)
        print(f"RealMathUniverse {VERSION}")
        print(f"Listening for VCV OSC on {self.host}:{self.port}")
        print(f"Project root: {self.project_root}")
        print(f"Output: {self.state_path}")
        print("Accepting explicit channels: /ch/1 through /ch/32")
        print("/ch/18 = behavior_code")
        print("/ch/19 = behavior_authority_gate")
        print("=" * 72)

        disp = dispatcher.Dispatcher()
        for i in range(1, 33):
            disp.map(f"/ch/{i}", self.handle_channel)
        disp.set_default_handler(self.generic_handler)

        writer = threading.Thread(target=self.writer_loop, daemon=True)
        writer.start()

        server = osc_server.ThreadingOSCUDPServer((self.host, self.port), disp)

        def stop_handler(signum: int, frame: Any) -> None:
            self.running = False
            server.shutdown()

        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)

        try:
            server.serve_forever()
        finally:
            self.running = False
            server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RealMathUniverse direct 32-channel VCV OSC bridge.")
    parser.add_argument("--project-root", default="/Users/Joe/Documents/RealMathUniverse")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--heartbeat", type=float, default=0.05)
    parser.add_argument("--active-timeout", type=float, default=1.5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bridge = VCVOSCBridge(
        project_root=Path(args.project_root).expanduser().resolve(),
        host=args.host,
        port=args.port,
        heartbeat=args.heartbeat,
        active_timeout=args.active_timeout,
    )
    bridge.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
