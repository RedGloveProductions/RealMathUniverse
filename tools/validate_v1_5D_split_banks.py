#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, subprocess, time
ROOT=Path("/Users/Joe/Documents/RealMathUniverse")
BRIDGE=ROOT/"src/control/vcv_osc_bridge.py"; SCHEMA=ROOT/"config/vcv_adaptive_schema.json"; STATE=ROOT/"output/vcv_state.json"; MAIN=ROOT/"metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
print("RealMathUniverse v1.5D 22-Voice Split Bank Validator")
print("="*92)
for label,path in [("bridge",BRIDGE),("schema",SCHEMA),("main.swift",MAIN),("state",STATE)]:
    print(f"{label} exists:", path.exists())
if BRIDGE.exists():
    txt=BRIDGE.read_text(errors="replace")
    for marker in ["v1.5D_22_voice_split_banks","split_22_bank",'"/ch/28": "probability_bank_B"','"/ch/29": "color_mode_bank_B"','"/ch/30": "particle_speed_bank_B"','"/ch/31": "particle_turbulence_bank_B"','"/ch/32": "particle_cohesion_bank_B"']:
        print(f"bridge marker {marker}:", marker in txt)
if SCHEMA.exists():
    data=json.loads(SCHEMA.read_text())
    print("schema version:", data.get("version"))
    for ch in ["/ch/1","/ch/7","/ch/9","/ch/10","/ch/11","/ch/12","/ch/13","/ch/16","/ch/17","/ch/28","/ch/29","/ch/30","/ch/31","/ch/32"]:
        print(ch, "=>", data.get("channels",{}).get(ch,{}).get("label"))
print("\nProcesses:")
try:
    out=subprocess.check_output(["/bin/zsh","-lc","pgrep -af 'vcv_osc_bridge.py|run_vcv_osc_bridge|RealMathUniverseMetalRenderer' || true"], text=True)
    print(out.strip() or "none")
except Exception as exc:
    print("process check failed:", exc)
if STATE.exists():
    d=json.loads(STATE.read_text()); now=time.time()
    print("\nstate version:", d.get("version")); print("mtime age:", round(now-STATE.stat().st_mtime,3)); print("active/fresh/stale:", d.get("active"), d.get("fresh"), d.get("stale")); print("status:", d.get("status")); print("split contract:", d.get("split_bank_contract"))
    for key in ["particle_species_probability","particle_species_color_mode","particle_species_speed","particle_species_mass","particle_species_turbulence","particle_species_cohesion","particle_species_color_hsl"]:
        value=d.get(key); print(f"{key} length:", len(value) if isinstance(value,list) else None)
    for ch in ["/ch/1","/ch/7","/ch/9","/ch/10","/ch/11","/ch/12","/ch/13","/ch/16","/ch/17","/ch/28","/ch/29","/ch/30","/ch/31","/ch/32"]:
        print(ch, "label:", d.get("native_channels",{}).get(ch), "voices:", d.get("channel_voice_counts",{}).get(ch))
