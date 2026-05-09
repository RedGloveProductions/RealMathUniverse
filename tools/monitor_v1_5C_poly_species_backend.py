#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
SPECIES = [
    "crab_default","electron","positron","electron_neutrino","up_quark","down_quark",
    "photon_like","gluon_like","higgs_excitation","proton_like","neutron_like","muon",
    "tau","muon_neutrino","tau_neutrino","strange_quark","charm_quark","top_quark",
    "bottom_quark","W_like","Z_like","meson_like"
]

def clear() -> None:
    print("\033[2J\033[H", end="")

def read(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return {"_error": "JSON decode error while bridge was writing"}

def fmt(xs: Any, n: int = 8) -> str:
    if not isinstance(xs, list):
        return "None"
    out = []
    for x in xs[:n]:
        if isinstance(x, (int, float)):
            out.append(f"{float(x):+.3f}")
        else:
            out.append(str(x))
    extra = "" if len(xs) <= n else f" ... +{len(xs)-n}"
    return "[" + ", ".join(out) + "]" + extra

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(ROOT))
    ap.add_argument("--interval", type=float, default=0.25)
    ap.add_argument("--no-clear", action="store_true")
    args = ap.parse_args()
    state = Path(args.project_root) / "output/vcv_state.json"
    try:
        while True:
            data = read(state)
            now = time.time()
            if not args.no_clear:
                clear()
            print("RealMathUniverse v1.5C POLY SPECIES BACKEND MONITOR")
            print("=" * 100)
            if data is None:
                print("No vcv_state.json")
                time.sleep(args.interval)
                continue
            if "_error" in data:
                print(data["_error"])
                time.sleep(args.interval)
                continue
            print(f"version: {data.get('version')}")
            print(f"mtime age: {now - state.stat().st_mtime:.3f}s  active={data.get('active')} fresh={data.get('fresh')} stale={data.get('stale')} status={data.get('status')}")
            print(f"messages={data.get('message_count')} writes={data.get('write_count')} scene={data.get('scene_index')} color={data.get('color_mode')}")
            print()
            print("CHANNELS")
            print("-" * 100)
            labels = data.get("native_channels", {})
            counts = data.get("channel_voice_counts", {})
            raw = data.get("raw_poly_channels", {})
            mapped = data.get("channels", {})
            for i in range(1, 18):
                addr = f"/ch/{i}"
                print(f"{addr:<6} {str(labels.get(addr)):<32} voices={str(counts.get(addr)):<3} mapped={str(mapped.get(addr)):<12} raw={fmt(raw.get(addr), 6)}")
            print()
            print("SPECIES BANK SUMMARY")
            print("-" * 100)
            for label, raw_key, mapped_key, vc_key in [
                ("probability", "particle_species_probability_raw", "particle_species_probability", "particle_species_probability_voice_count"),
                ("color_mode", "particle_species_color_mode_raw", "particle_species_color_mode", "particle_species_color_mode_voice_count"),
                ("speed", "particle_species_speed_raw", "particle_species_speed", "particle_species_speed_voice_count"),
                ("mass", "particle_species_mass_raw", "particle_species_mass", "particle_species_mass_voice_count"),
                ("turbulence", "particle_species_turbulence_raw", "particle_species_turbulence", "particle_species_turbulence_voice_count"),
                ("cohesion", "particle_species_cohesion_raw", "particle_species_cohesion", "particle_species_cohesion_voice_count"),
                ("color_hsl", "particle_species_color_hsl_raw", "particle_species_color_hex", "particle_species_color_hsl_voice_count"),
            ]:
                print(f"{label:<12} voices={data.get(vc_key)} raw={fmt(data.get(raw_key), 5)} mapped={fmt(data.get(mapped_key), 5)}")
            print()
            print("PER-SPECIES P/S/M/T/C/COLOR")
            print("-" * 100)
            mass = data.get("particle_species_mass") or []
            speed = data.get("particle_species_speed") or []
            prob = data.get("particle_species_probability") or []
            turb = data.get("particle_species_turbulence") or []
            coh = data.get("particle_species_cohesion") or []
            hexes = data.get("particle_species_color_hex") or []
            for i, name in enumerate(SPECIES):
                print(
                    f"{i+1:02d} {name:<22} "
                    f"P={prob[i] if i < len(prob) else None!s:<7} "
                    f"S={speed[i] if i < len(speed) else None!s:<7} "
                    f"M={mass[i] if i < len(mass) else None!s:<7} "
                    f"T={turb[i] if i < len(turb) else None!s:<7} "
                    f"C={coh[i] if i < len(coh) else None!s:<7} "
                    f"HEX={hexes[i] if i < len(hexes) else None}"
                )
            print()
            print(f"gravity_vec4={fmt(data.get('gravity_well_position_vec4'), 4)} raw={fmt(data.get('gravity_well_position_raw_vec4'), 4)} strength={data.get('gravity_well_strength')}")
            print("CTRL+C to stop.")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
