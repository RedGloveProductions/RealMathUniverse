#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
SCHEMA = ROOT / "config/vcv_adaptive_schema.json"
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
STATE = ROOT / "output/vcv_state.json"

print("RealMathUniverse v1.5C Poly Species Backend Validator")
print("=" * 88)

for label, path in [("bridge", BRIDGE), ("schema", SCHEMA), ("main.swift", MAIN), ("state", STATE)]:
    print(f"{label} exists:", path.exists())

if BRIDGE.exists():
    txt = BRIDGE.read_text(errors="replace")
    for marker in [
        "v1.5C_poly_species_control_backend",
        "particle_species_probability",
        "particle_species_speed",
        "particle_species_turbulence",
        "particle_species_cohesion",
        "gravity_well_position_vec4",
        "species_color_hsl_bank_A",
    ]:
        print(f"bridge marker {marker}:", marker in txt)

if SCHEMA.exists():
    data = json.loads(SCHEMA.read_text())
    print("schema version:", data.get("version"))
    for ch in ["/ch/1","/ch/7","/ch/9","/ch/10","/ch/11","/ch/12","/ch/13","/ch/14","/ch/15","/ch/16","/ch/17"]:
        print(ch, "=>", data.get("channels", {}).get(ch, {}).get("label"))

if MAIN.exists():
    txt = MAIN.read_text(errors="replace")
    print("Swift v1.5C state marker:", "RMU_V1_5C_POLY_SPECIES_CONTROL_STATE" in txt)
    print("Swift v1.5C parser marker:", "RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE" in txt)

print()
print("Processes:")
try:
    out = subprocess.check_output(["/bin/zsh","-lc","pgrep -af 'vcv_osc_bridge.py|run_vcv_osc_bridge|RealMathUniverseMetalRenderer' || true"], text=True)
    print(out.strip() or "none")
except Exception as exc:
    print("process check failed:", exc)

if STATE.exists():
    d = json.loads(STATE.read_text())
    now = time.time()
    print()
    print("state version:", d.get("version"))
    print("mtime age:", round(now - STATE.stat().st_mtime, 3))
    print("active/fresh/stale:", d.get("active"), d.get("fresh"), d.get("stale"))
    print("status:", d.get("status"))
    for key in [
        "particle_species_probability",
        "particle_species_color_mode",
        "particle_species_speed",
        "particle_species_mass",
        "particle_species_turbulence",
        "particle_species_cohesion",
        "particle_species_color_hsl",
        "gravity_well_position_vec4",
    ]:
        value = d.get(key)
        print(f"{key} length:", len(value) if isinstance(value, list) else None)
    for ch in ["/ch/1","/ch/7","/ch/9","/ch/10","/ch/11","/ch/12","/ch/13","/ch/14","/ch/15","/ch/16","/ch/17"]:
        print(ch, "label:", d.get("native_channels", {}).get(ch), "voices:", d.get("channel_voice_counts", {}).get(ch))
