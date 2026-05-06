#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}

control = load(ROOT / "output" / "control_state.json")
runtime = load(ROOT / "output" / "runtime_state.json")
vcv = load(ROOT / "output" / "vcv_state.json")

print("RealMathUniverse v1.3F9H stable milestone quick check")
print()
print("control_state:")
for key in [
    "behavior_enabled",
    "behavior_effect_code",
    "behavior_mode",
    "behavior_bypass_authority",
    "respawn_on_capture",
    "particle_speed",
    "particle_mass",
    "particle_turbulence",
    "particle_cohesion",
    "runtime_mode",
]:
    print(f"  {key}: {control.get(key)}")

print()
print("runtime_state:")
for key in ["behavior_enabled", "behavior_effect_code", "respawn_on_capture", "runtime_mode"]:
    print(f"  {key}: {runtime.get(key)}")

print()
print("vcv_state:")
for key in ["external_detected", "particle_speed", "particle_mass", "particle_turbulence", "particle_cohesion"]:
    print(f"  {key}: {vcv.get(key)}")

print()
print("Expected stable signs:")
print("  behavior OFF test: behavior_enabled=false and behavior_effect_code=0")
print("  VCV active test: /ch/9-/ch/12 values change while behavior_effect_code stays 0")
