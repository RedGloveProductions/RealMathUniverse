#!/usr/bin/env python3
from __future__ import annotations
import json, time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [root / "output" / "vcv_state.json", root / "output" / "control_state.json"]

def load(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = find_key(value, key)
            if found is not None:
                return found
    return None

print("Move VCV /ch/11 and /ch/12. Sampling live state...")
for i in range(10):
    print(f"sample {i+1}")
    for path in paths:
        data = load(path)
        print(" ", path.name)
        for key in ["particle_turbulence_raw", "particle_turbulence", "particle_cohesion_raw", "particle_cohesion"]:
            print(f"    {key}: {find_key(data, key)}")
        print(f"    aux /ch/11: {find_key(data, '/ch/11')}")
        print(f"    aux /ch/12: {find_key(data, '/ch/12')}")
    time.sleep(0.75)
