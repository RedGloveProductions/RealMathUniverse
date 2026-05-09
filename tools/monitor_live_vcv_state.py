#!/usr/bin/env python3
"""
RealMathUniverse Live VCV State Monitor

Run from the RealMathUniverse project root while the simulator is running:

    cd /Users/Joe/Documents/RealMathUniverse
    source .venv/bin/activate
    python3 tools/monitor_live_vcv_state.py

Optional:
    python3 tools/monitor_live_vcv_state.py --interval 0.25
    python3 tools/monitor_live_vcv_state.py --watch-channel /ch/13
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_PROJECT_ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
DEFAULT_STATE_FILE = "output/vcv_state.json"


def clear_screen() -> None:
    print("\033[2J\033[H", end="")


def fmt_bool(value: Any) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return "None"


def fmt_age(now: float, timestamp: Any) -> str:
    if timestamp is None:
        return "None"
    try:
        age = now - float(timestamp)
        return f"{age:0.3f}s"
    except Exception:
        return "bad"


def fmt_list(values: Any, precision: int = 3, max_items: int = 8) -> str:
    if not isinstance(values, list):
        return "None"
    shown = values[:max_items]
    parts = []
    for value in shown:
        if isinstance(value, (int, float)):
            parts.append(f"{float(value):+.{precision}f}")
        else:
            parts.append(str(value))
    suffix = "" if len(values) <= max_items else f" ... +{len(values) - max_items}"
    return "[" + ", ".join(parts) + "]" + suffix


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            return obj
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return {"_error": "JSON decode error while bridge was writing. Try again next tick."}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}
    return {"_error": "State file did not contain a JSON object."}


def get_channel_summary(data: Dict[str, Any], address: str) -> Dict[str, Any]:
    details = data.get("channel_details", {})
    raw_poly = data.get("raw_poly_channels", {})
    voice_counts = data.get("channel_voice_counts", {})
    labels = data.get("native_channels", {}) or data.get("labels", {})
    channels = data.get("channels", {})
    raw_channels = data.get("raw", {})

    return {
        "label": labels.get(address),
        "voice_count": voice_counts.get(address),
        "raw_poly": raw_poly.get(address),
        "mapped_scalar": channels.get(address),
        "raw_scalar": raw_channels.get(address),
        "details": details.get(address, {}),
    }


def print_header(path: Path, now: float, data: Dict[str, Any]) -> None:
    try:
        mtime_age = now - path.stat().st_mtime
    except Exception:
        mtime_age = None

    print("RealMathUniverse LIVE VCV STATE MONITOR")
    print("=" * 78)
    print(f"state file: {path}")
    print(f"file mtime age: {mtime_age:0.3f}s" if mtime_age is not None else "file mtime age: None")
    print(f"version: {data.get('version')}")
    print("-" * 78)
    print(f"active: {fmt_bool(data.get('active'))}   fresh: {fmt_bool(data.get('fresh'))}   stale: {fmt_bool(data.get('stale'))}")
    print(f"status: {data.get('status')}   vcv_status: {data.get('vcv_status')}")
    print(f"external_detected: {fmt_bool(data.get('external_detected'))}   probability_source: {data.get('probability_source')}")
    print(f"timestamp_unix age: {fmt_age(now, data.get('timestamp_unix'))}")
    print(f"last_update age:    {fmt_age(now, data.get('last_update'))}")
    print(f"last_message age:   {fmt_age(now, data.get('last_message_time'))}")
    print(f"message_count: {data.get('message_count')}   write_count: {data.get('write_count')}")
    print(f"active_channel_count: {data.get('active_channel_count')}")
    print(f"active_channels: {data.get('active_channels')}")
    print()


def print_core_controls(data: Dict[str, Any]) -> None:
    print("CORE CONTROLS")
    print("-" * 78)
    print(f"probability:               {data.get('probability')}   raw: {data.get('probability_raw')}")
    print(f"field_layer_weights:       {fmt_list(data.get('field_layer_weights'), precision=3, max_items=8)}")
    print(f"particle_speed:            {data.get('particle_speed')}   raw: {data.get('particle_speed_raw')}")
    print(f"particle_mass:             {data.get('particle_mass')}   raw: {data.get('particle_mass_raw')}")
    print(f"particle_turbulence:       {data.get('particle_turbulence')}   raw: {data.get('particle_turbulence_raw')}")
    print(f"particle_cohesion:         {data.get('particle_cohesion')}   raw: {data.get('particle_cohesion_raw')}")
    print(f"gravity_well_position:     {data.get('gravity_well_position')}")
    print(f"gravity_well_position3:    {fmt_list(data.get('gravity_well_position_vec3'), precision=3, max_items=3)}")
    print(f"gravity_well_position3 raw:{fmt_list(data.get('gravity_well_position_raw_vec3'), precision=3, max_items=3)}")
    print(f"gravity_well_strength:     {data.get('gravity_well_strength')}   raw: {data.get('gravity_well_strength_raw')}")
    print()


def print_channels(data: Dict[str, Any], max_channels: int = 16) -> None:
    print(f"CHANNELS /ch/1 - /ch/{max_channels}")
    print("-" * 78)
    print(f"{'addr':<7} {'label':<24} {'voices':<6} {'raw poly':<32} {'mapped':<10}")
    print("-" * 78)

    for i in range(1, max_channels + 1):
        addr = f"/ch/{i}"
        s = get_channel_summary(data, addr)
        label = str(s["label"] or "")
        voices = str(s["voice_count"] if s["voice_count"] is not None else "")
        raw_poly = fmt_list(s["raw_poly"], precision=3, max_items=4)
        mapped = s["mapped_scalar"]
        if isinstance(mapped, (int, float)):
            mapped_text = f"{float(mapped):+.3f}"
        else:
            mapped_text = str(mapped)

        print(f"{addr:<7} {label:<24.24} {voices:<6} {raw_poly:<32.32} {mapped_text:<10}")
    print()


def print_watch_channel(data: Dict[str, Any], address: str) -> None:
    s = get_channel_summary(data, address)
    print(f"DETAIL WATCH: {address}")
    print("-" * 78)
    print(f"label:         {s['label']}")
    print(f"voice_count:   {s['voice_count']}")
    print(f"raw_poly:      {fmt_list(s['raw_poly'], precision=6, max_items=16)}")
    print(f"raw_scalar:    {s['raw_scalar']}")
    print(f"mapped_scalar: {s['mapped_scalar']}")

    details = s.get("details") or {}
    if details:
        print(f"detected_shape:        {details.get('detected_shape')}")
        print(f"detected_voltage_mode: {details.get('detected_voltage_mode')}")
        print(f"detected_motion:       {details.get('detected_motion')}")
        print(f"fresh:                 {details.get('fresh')}")
        print(f"rising_edge:           {details.get('rising_edge')}")
        print(f"falling_edge:          {details.get('falling_edge')}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor RealMathUniverse live VCV state.")
    parser.add_argument("--project-root", default=str(DEFAULT_PROJECT_ROOT))
    parser.add_argument("--state", default=DEFAULT_STATE_FILE)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--channels", type=int, default=16)
    parser.add_argument("--watch-channel", default="/ch/13")
    parser.add_argument("--no-clear", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).expanduser().resolve()
    state_path = Path(args.state)
    if not state_path.is_absolute():
        state_path = project_root / state_path

    try:
        while True:
            now = time.time()
            data = read_json(state_path)

            if not args.no_clear:
                clear_screen()

            if data is None:
                print("RealMathUniverse LIVE VCV STATE MONITOR")
                print("=" * 78)
                print(f"Waiting for state file: {state_path}")
                print("The simulator or VCV bridge may not be running yet.")
                time.sleep(args.interval)
                continue

            if "_error" in data:
                print("RealMathUniverse LIVE VCV STATE MONITOR")
                print("=" * 78)
                print(f"state file: {state_path}")
                print(f"ERROR: {data['_error']}")
                time.sleep(args.interval)
                continue

            print_header(state_path, now, data)
            print_core_controls(data)
            print_channels(data, max_channels=max(1, min(args.channels, 32)))
            print_watch_channel(data, args.watch_channel)
            print("Press CTRL+C to stop.")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped live VCV monitor.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
