#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
SPECIES = ["crab_default","electron","positron","electron_neutrino","up_quark","down_quark","photon_like","gluon_like","higgs_excitation","proton_like","neutron_like","muon","tau","muon_neutrino","tau_neutrino","strange_quark","charm_quark","top_quark","bottom_quark","W_like","Z_like","meson_like"]

def clear(): print("\033[2J\033[H", end="")
def read(path: Path) -> Optional[Dict[str, Any]]:
    try: return json.loads(path.read_text())
    except FileNotFoundError: return None
    except json.JSONDecodeError: return {"_error":"JSON decode error while bridge was writing"}
def fmt(xs: Any, n: int=8) -> str:
    if not isinstance(xs, list): return "None"
    out=[]
    for x in xs[:n]:
        out.append(f"{float(x):+.3f}" if isinstance(x,(int,float)) else str(x))
    return "["+", ".join(out)+("]" if len(xs)<=n else f" ... +{len(xs)-n}]")

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(ROOT))
    ap.add_argument("--interval", type=float, default=0.25)
    ap.add_argument("--no-clear", action="store_true")
    args=ap.parse_args()
    state=Path(args.project_root)/"output/vcv_state.json"
    try:
        while True:
            data=read(state); now=time.time()
            if not args.no_clear: clear()
            print("RealMathUniverse v1.5D 22-VOICE SPLIT BANK MONITOR")
            print("="*108)
            if data is None:
                print("No vcv_state.json"); time.sleep(args.interval); continue
            if "_error" in data:
                print(data["_error"]); time.sleep(args.interval); continue
            print(f"version: {data.get('version')}")
            print(f"mtime age: {now-state.stat().st_mtime:.3f}s active={data.get('active')} fresh={data.get('fresh')} stale={data.get('stale')} status={data.get('status')}")
            print(f"messages={data.get('message_count')} writes={data.get('write_count')} scene={data.get('scene_index')} color={data.get('color_mode')}")
            print(f"summary: {data.get('summary')}\n")
            labels=data.get("native_channels",{}); counts=data.get("channel_voice_counts",{}); raw=data.get("raw_poly_channels",{}); mapped=data.get("channels",{})
            print("CHANNELS")
            print("-"*108)
            for i in list(range(1,18))+list(range(28,33)):
                addr=f"/ch/{i}"
                print(f"{addr:<6} {str(labels.get(addr)):<34} voices={str(counts.get(addr)):<3} mapped={str(mapped.get(addr)):<12} raw={fmt(raw.get(addr),6)}")
            print("\nSPLIT BANK SUMMARY")
            print("-"*108)
            rows=[
                ("probability","particle_species_probability_voice_count_A","particle_species_probability_voice_count_B","particle_species_probability_raw","particle_species_probability"),
                ("color_mode","particle_species_color_mode_voice_count_A","particle_species_color_mode_voice_count_B","particle_species_color_mode_raw","particle_species_color_mode"),
                ("speed","particle_species_speed_voice_count_A","particle_species_speed_voice_count_B","particle_species_speed_raw","particle_species_speed"),
                ("mass","particle_species_mass_voice_count_A","particle_species_mass_voice_count_B","particle_species_mass_raw","particle_species_mass"),
                ("turbulence","particle_species_turbulence_voice_count_A","particle_species_turbulence_voice_count_B","particle_species_turbulence_raw","particle_species_turbulence"),
                ("cohesion","particle_species_cohesion_voice_count_A","particle_species_cohesion_voice_count_B","particle_species_cohesion_raw","particle_species_cohesion"),
                ("color_hsl","particle_species_color_hsl_voice_count_A","particle_species_color_hsl_voice_count_B","particle_species_color_hsl_raw","particle_species_color_hex"),
            ]
            for label,a,b,raw_key,map_key in rows:
                print(f"{label:<12} voices={data.get(a)}+{data.get(b)} raw={fmt(data.get(raw_key),5)} mapped={fmt(data.get(map_key),5)}")
            print("\nPER-SPECIES P/S/M/T/C/COLOR")
            print("-"*108)
            mass=data.get("particle_species_mass") or []; speed=data.get("particle_species_speed") or []; prob=data.get("particle_species_probability") or []
            turb=data.get("particle_species_turbulence") or []; coh=data.get("particle_species_cohesion") or []; hexes=data.get("particle_species_color_hex") or []
            for i,name in enumerate(SPECIES):
                print(f"{i+1:02d} {name:<22} P={prob[i] if i<len(prob) else None!s:<7} S={speed[i] if i<len(speed) else None!s:<7} M={mass[i] if i<len(mass) else None!s:<7} T={turb[i] if i<len(turb) else None!s:<7} C={coh[i] if i<len(coh) else None!s:<7} HEX={hexes[i] if i<len(hexes) else None}")
            print(f"\ngravity_vec4={fmt(data.get('gravity_well_position_vec4'),4)} raw={fmt(data.get('gravity_well_position_raw_vec4'),4)} strength={data.get('gravity_well_strength')}")
            print("CTRL+C to stop.")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped."); return 0
if __name__=="__main__": raise SystemExit(main())
